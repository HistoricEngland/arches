"""
ARCHES - a program developed to inventory and manage immovable cultural heritage.
Copyright (C) 2013 J. Paul Getty Trust and World Monuments Fund

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import uuid
import importlib
import datetime
import logging
from time import time
from uuid import UUID
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.models import User, Group, Permission
from django.forms.models import model_to_dict
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from arches.app.models import models
from arches.app.models.models import EditLog
from arches.app.models.models import TileModel
from arches.app.models.concept import get_preflabel_from_valueid
from arches.app.models.system_settings import settings
from arches.app.search.search_engine_factory import SearchEngineInstance as se
from arches.app.search.mappings import TERMS_INDEX, RESOURCES_INDEX
from arches.app.search.elasticsearch_dsl_builder import Query, Bool, Terms, Nested
from arches.app.tasks import index_resource
from arches.app.utils import import_class_from_string, task_management
from arches.app.utils.label_based_graph import LabelBasedGraph
from arches.app.utils.label_based_graph_v2 import LabelBasedGraph as LabelBasedGraphV2
from guardian.shortcuts import assign_perm, remove_perm
from guardian.exceptions import NotUserNorGroup
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.utils.exceptions import (
    InvalidNodeNameException,
    MultipleNodesFoundException,
)
from arches.app.utils.permission_backend import (
    user_is_resource_reviewer,
    get_restricted_users,
    get_restricted_instances,
    user_can_read_resource,
)
from arches.app.datatypes.datatypes import DataTypeFactory

logger = logging.getLogger(__name__)


class Resource(models.ResourceInstance):
    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(Resource, self).__init__(*args, **kwargs)
        # from models.ResourceInstance
        # self.resourceinstanceid
        # self.graph
        # self.resourceinstancesecurity
        # end from models.ResourceInstance
        self.tiles = []

    def get_descriptor(self, descriptor, context):
        graph_function = models.FunctionXGraph.objects.filter(
            graph_id=self.graph_id, function__functiontype="primarydescriptors"
        ).select_related("function")

        if self.descriptors is None:
            self.descriptors = {}

        if len(graph_function) == 1:
            module = graph_function[0].function.get_class_module()()

            return module.get_primary_descriptor_from_nodes(self, graph_function[0].config["descriptor_types"][descriptor], context)

        else:
            self.descriptors[descriptor] = "undefined"

        return self.descriptors[descriptor]

    def displaydescription(self, context=None):
        return self.get_descriptor("description", context)

    def map_popup(self, context=None):
        return self.get_descriptor("map_popup", context)

    def displayname(self, context=None):
        descriptor = self.get_descriptor("name", context)
        self.name = descriptor
        return descriptor

    def save_edit(self, user={}, note="", edit_type="", transaction_id=None):
        timestamp = datetime.datetime.now()
        edit = EditLog()
        edit.resourceclassid = self.graph_id
        edit.resourceinstanceid = self.resourceinstanceid
        edit.userid = getattr(user, "id", "")
        edit.user_email = getattr(user, "email", "")
        edit.user_firstname = getattr(user, "first_name", "")
        edit.user_lastname = getattr(user, "last_name", "")
        edit.note = note
        edit.timestamp = timestamp
        if transaction_id is not None:
            edit.transactionid = transaction_id
        edit.edittype = edit_type
        edit.save()

    def save(self, *args, **kwargs):
        """
        Saves and indexes a single resource

        Keyword Arguments:
        request -- the request object
        user -- the user to associate the edit with if the user can't be derived from the request
        index -- True(default) to index the resource, otherwise don't index the resource

        """
        graph = models.GraphModel.objects.get(graphid=self.graph_id)
        if graph.isactive is False:
            message = _("This model is not yet active; unable to save.")
            raise ModelInactiveError(message)
        request = kwargs.pop("request", None)
        user = kwargs.pop("user", None)
        index = kwargs.pop("index", True)
        context = kwargs.pop("context", None)
        transaction_id = kwargs.pop("transaction_id", None)
        super(Resource, self).save(*args, **kwargs)
        for tile in self.tiles:
            tile.resourceinstance_id = self.resourceinstanceid
            tile.save(request=request, index=False, transaction_id=transaction_id, context=context)
        if request is None:
            if user is None:
                user = {}
        else:
            user = request.user

        try:
            for perm in ("view_resourceinstance", "change_resourceinstance", "delete_resourceinstance"):
                assign_perm(perm, user, self)
        except NotUserNorGroup:
            pass

        self.save_edit(user=user, edit_type="create", transaction_id=transaction_id)
        if index is True:
            self.index(context)

    def get_root_ontology(self):
        """
        Finds and returns the ontology class of the instance's root node

        """
        root_ontology_class = None
        graph_nodes = models.Node.objects.filter(graph_id=self.graph_id).filter(istopnode=True)
        if len(graph_nodes) > 0:
            root_ontology_class = graph_nodes[0].ontologyclass

        return root_ontology_class

    def load_tiles(self, user=None, perm=None):
        """
        Loads the resource's tiles array with all the tiles from the database as a flat list

        """

        self.tiles = list(models.TileModel.objects.filter(resourceinstance=self))
        if user:
            self.tiles = [tile for tile in self.tiles if tile.nodegroup_id is not None and user.has_perm(perm, tile.nodegroup)]

    # # flatten out the nested tiles into a single array
    def get_flattened_tiles(self):
        tiles = []
        for tile in self.tiles:
            tiles.extend(tile.get_flattened_tiles())
        return tiles

    @staticmethod
    def bulk_save(resources, transaction_id=None, prevent_indexing=False):
        """
        Saves and indexes a list of resources

        Arguments:
        resources -- a list of resource models

        Keyword Arguments:
        transaction_id -- a uuid identifing the save of these instances as belonging to a collective load or process

        """

        datatype_factory = DataTypeFactory()
        node_datatypes = {str(nodeid): datatype for nodeid, datatype in models.Node.objects.values_list("nodeid", "datatype")}
        tiles = []
        documents = []
        term_list = []

        for resource in resources:
            resource.tiles = resource.get_flattened_tiles()
            tiles.extend(resource.tiles)

        # need to handle if the bulk load is appending tiles to existing resources/
        existing_resources_ids = Resource.objects.filter(
            resourceinstanceid__in=[resource.resourceinstanceid for resource in resources]
        ).values_list("resourceinstanceid", flat=True)

        existing_resources = [resource for resource in resources if resource.resourceinstanceid in existing_resources_ids]
        resources_to_create = [resource for resource in resources if resource.resourceinstanceid not in existing_resources_ids]

        start = time()
        Resource.objects.bulk_create(resources_to_create)

        # need to run logic in pre_tile_save fro the datatypes otherwise resource relationships and file aren't loaded correctly.
        # Needs to be some kind of bulk_pre_tile_save
        for tile in tiles:
            for nodeid in tile.data.keys():
                try:
                    node_datatype = datatype_factory.get_instance(node_datatypes[nodeid])
                    node_datatype.pre_tile_save(tile, nodeid)
                except:
                    pass

        TileModel.objects.bulk_create(tiles)

        logger.info(f"Time to bulk save tiles and resources: {datetime.timedelta(seconds=time() - start)}")

        start = time()
        for resource in resources_to_create:
            resource.save_edit(edit_type="create", transaction_id=transaction_id)

        try:
            resources[0].tiles[0].save_edit(
                note=f"Bulk created: {len(tiles)} for {len(resources)} resources.",
                edit_type="bulk_create",
                transaction_id=transaction_id,
            )
        except:
            pass

        logger.info("Time to save resource edits: %s" % datetime.timedelta(seconds=time() - start))
        if not prevent_indexing:
            for resource in resources:
                start = time()
                document, terms = resource.get_documents_to_index(
                    fetchTiles=False, datatype_factory=datatype_factory, node_datatypes=node_datatypes
                )

                documents.append(se.create_bulk_item(index=RESOURCES_INDEX, id=document["resourceinstanceid"], data=document))

                for term in terms:
                    term_list.append(se.create_bulk_item(index=TERMS_INDEX, id=term["_id"], data=term["_source"]))

            se.bulk_index(documents)
            se.bulk_index(term_list)
        else:
            logger.info("... defering indexing in resource bulk save")

    def index(self, context=None):
        """
        Indexes all the nessesary items values of a resource to support search

        Keyword Arguments:
        context -- a string such as "copy" to indicate conditions under which a document is indexed

        """

        if str(self.graph_id) != str(settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID):
            datatype_factory = DataTypeFactory()
            node_datatypes = {str(nodeid): datatype for nodeid, datatype in models.Node.objects.values_list("nodeid", "datatype")}
            document, terms = self.get_documents_to_index(datatype_factory=datatype_factory, node_datatypes=node_datatypes, context=context)
            document["root_ontology_class"] = self.get_root_ontology()
            doc = JSONSerializer().serializeToPython(document)
            se.index_data(index=RESOURCES_INDEX, body=doc, id=self.pk)
            for term in terms:
                se.index_data("terms", body=term["_source"], id=term["_id"])

            if len(settings.ELASTICSEARCH_CUSTOM_INDEXES) > 0:
                celery_worker_running = task_management.check_if_celery_available()

                for index in settings.ELASTICSEARCH_CUSTOM_INDEXES:
                    if celery_worker_running and index.get("should_update_asynchronously"):
                        index_resource.apply_async([index["module"], index["name"], self.pk, [tile.pk for tile in document["tiles"]]])
                    else:
                        es_index = import_class_from_string(index["module"])(index["name"])
                        doc, doc_id = es_index.get_documents_to_index(self, document["tiles"])
                        es_index.index_document(document=doc, id=doc_id)

            super(Resource, self).save()

    def get_documents_to_index(self, fetchTiles=True, datatype_factory=None, node_datatypes=None, context=None):
        """
        Gets all the documents nessesary to index a single resource
        returns a tuple of a document and list of terms

        Keyword Arguments:
        fetchTiles -- instead of fetching the tiles from the database get them off the model itself
        datatype_factory -- refernce to the DataTypeFactory instance
        node_datatypes -- a dictionary of datatypes keyed to node ids
        context -- a string such as "copy" to indicate conditions under which a document is indexed

        """

        document = {}
        document["displaydescription"] = None
        document["resourceinstanceid"] = str(self.resourceinstanceid)
        document["graph_id"] = str(self.graph_id)
        document["map_popup"] = None
        document["displayname"] = None
        document["root_ontology_class"] = self.get_root_ontology()
        document["legacyid"] = self.legacyid
        document["displayname"] = self.displayname(context)
        document["displaydescription"] = self.displaydescription(context)
        document["map_popup"] = self.map_popup(context)

        tiles = list(models.TileModel.objects.filter(resourceinstance=self)) if fetchTiles else self.tiles

        restrictions = get_restricted_users(self)
        document["tiles"] = tiles
        document["permissions"] = {"users_without_read_perm": restrictions["cannot_read"]}
        document["permissions"]["users_without_edit_perm"] = restrictions["cannot_write"]
        document["permissions"]["users_without_delete_perm"] = restrictions["cannot_delete"]
        document["permissions"]["users_with_no_access"] = restrictions["no_access"]
        document["strings"] = []
        document["dates"] = []
        document["domains"] = []
        document["geometries"] = []
        document["points"] = []
        document["numbers"] = []
        document["date_ranges"] = []
        document["ids"] = []
        document["provisional_resource"] = "true" if sum([len(t.data) for t in tiles]) == 0 else "false"

        terms = []

        for tile in document["tiles"]:
            for nodeid, nodevalue in tile.data.items():
                if nodevalue != "" and nodevalue != [] and nodevalue != {} and nodevalue is not None:
                    datatype = node_datatypes[nodeid]
                    datatype_instance = datatype_factory.get_instance(datatype)
                    datatype_instance.append_to_document(document, nodevalue, nodeid, tile)
                    node_terms = datatype_instance.get_search_terms(nodevalue, nodeid)
                    for index, term in enumerate(node_terms):
                        terms.append(
                            {
                                "_id": str(nodeid) + str(tile.tileid) + str(index),
                                "_source": {
                                    "value": term,
                                    "nodeid": nodeid,
                                    "nodegroupid": tile.nodegroup_id,
                                    "tileid": tile.tileid,
                                    "resourceinstanceid": tile.resourceinstance_id,
                                    "provisional": False,
                                },
                            }
                        )

            if tile.provisionaledits is not None:
                provisionaledits = tile.provisionaledits
                if len(provisionaledits) > 0:
                    if document["provisional_resource"] == "false":
                        document["provisional_resource"] = "partial"
                    for user, edit in provisionaledits.items():
                        if edit["status"] == "review":
                            for nodeid, nodevalue in edit["value"].items():
                                if nodevalue != "" and nodevalue != [] and nodevalue != {} and nodevalue is not None:
                                    datatype = node_datatypes[nodeid]
                                    datatype_instance = datatype_factory.get_instance(datatype)
                                    datatype_instance.append_to_document(document, nodevalue, nodeid, tile, True)
                                    node_terms = datatype_instance.get_search_terms(nodevalue, nodeid)
                                    for index, term in enumerate(node_terms):
                                        terms.append(
                                            {
                                                "_id": str(nodeid) + str(tile.tileid) + str(index),
                                                "_source": {
                                                    "value": term,
                                                    "nodeid": nodeid,
                                                    "nodegroupid": tile.nodegroup_id,
                                                    "tileid": tile.tileid,
                                                    "resourceinstanceid": tile.resourceinstance_id,
                                                    "provisional": True,
                                                },
                                            }
                                        )

        return document, terms

    def delete(self, user={}, index=True, transaction_id=None):
        """
        Deletes a single resource and any related indexed data

        """

        # note that deferring index will require:
        # - that any resources related to the to-be-deleted resource get re-indexed
        # - that the index for the to-be-deleted resource gets deleted

        permit_deletion = False
        graph = models.GraphModel.objects.get(graphid=self.graph_id)
        if graph.isactive is False:
            message = _("This model is not yet active; unable to delete.")
            raise ModelInactiveError(message)
        if user != {}:
            user_is_reviewer = user_is_resource_reviewer(user)
            if user_is_reviewer is False:
                tiles = list(models.TileModel.objects.filter(resourceinstance=self))
                resource_is_provisional = True if sum([len(t.data) for t in tiles]) == 0 else False
                if resource_is_provisional is True:
                    permit_deletion = True
            else:
                permit_deletion = True
        else:
            permit_deletion = True

        if permit_deletion is True:
            for related_resource in models.ResourceXResource.objects.filter(
                Q(resourceinstanceidfrom=self.resourceinstanceid) | Q(resourceinstanceidto=self.resourceinstanceid)
            ):
                related_resource.delete(deletedResourceId=self.resourceinstanceid)

            if index:
                self.delete_index()

            try:
                self.save_edit(edit_type="delete", user=user, note=self.displayname(), transaction_id=transaction_id)
            except:
                pass
            super(Resource, self).delete()

        return permit_deletion

    def delete_index(self, resourceinstanceid=None):
        """
        Deletes all references to a resource from all indexes

        Keyword Arguments:
        resourceinstanceid -- the resource instance id to delete from related indexes, if supplied will use this over self.resourceinstanceid
        """

        if resourceinstanceid is None:
            resourceinstanceid = self.resourceinstanceid
        resourceinstanceid = str(resourceinstanceid)

        # delete any related terms
        query = Query(se)
        bool_query = Bool()
        bool_query.filter(Terms(field="resourceinstanceid", terms=[resourceinstanceid]))
        query.add_query(bool_query)
        query.delete(index=TERMS_INDEX)

        # reindex any related resources
        query = Query(se)
        bool_query = Bool()
        bool_query.filter(Nested(path="ids", query=Terms(field="ids.id", terms=[resourceinstanceid])))
        query.add_query(bool_query)
        results = query.search(index=RESOURCES_INDEX)["hits"]["hits"]
        for result in results:
            try:
                res = Resource.objects.get(pk=result["_id"])
                res.load_tiles()
                res.index()
            except ObjectDoesNotExist:
                pass

        # delete resource index
        se.delete(index=RESOURCES_INDEX, id=resourceinstanceid)

        # delete resources from custom indexes
        for index in settings.ELASTICSEARCH_CUSTOM_INDEXES:
            es_index = import_class_from_string(index["module"])(index["name"])
            es_index.delete_resources(resources=self)

    def validate(self, verbose=False, strict=False):
        """
        Keyword Arguments:
        verbose -- False(default) to only show the first error thrown in any tile, True to show all the errors in all the tiles
        strict -- False(default), True to use a more complete check on the datatype
            (eg: check for the existance of a referenced resoure on the resource-instance datatype)
        """

        from arches.app.models.tile import Tile, TileValidationError

        errors = []
        tiles = self.tiles
        if len(self.tiles) == 0:
            tiles = Tile.objects.filter(resourceinstance=self)

        for tile in tiles:
            try:
                tile.validate(raise_early=(not verbose), strict=strict)
            except TileValidationError as err:
                errors += err.message if isinstance(err.message, list) else [err.message]
        return errors

    def get_related_resources(
        self,
        lang="en-US",
        limit=settings.RELATED_RESOURCES_EXPORT_LIMIT,
        start=0,
        page=0,
        user=None,
        resourceinstance_graphid=None,
        graphs=None,
    ):
        """
        Returns an object that lists the related resources, the relationship types, and a reference to the current resource

        """
        if not graphs:
            graphs = list(
                models.GraphModel.objects.all()
                .exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
                .exclude(isresource=False)
                .exclude(isactive=False)
            )

        graph_lookup = {
            str(graph.graphid): {"name": graph.name, "iconclass": graph.iconclass, "fillColor": graph.color} for graph in graphs
        }

        ret = {"resource_instance": self, "resource_relationships": [], "related_resources": [], "node_config_lookup": graph_lookup}

        if page > 0:
            number_per_page = settings.RELATED_RESOURCES_PER_PAGE
            start = number_per_page * int(page - 1)
            limit = number_per_page * page

        def get_relations(resourceinstanceid, start, limit, resourceinstance_graphid=None):
            final_query = Q(resourceinstanceidfrom_id=resourceinstanceid) | Q(resourceinstanceidto_id=resourceinstanceid)

            if resourceinstance_graphid:
                to_graph_id_filter = Q(resourceinstancefrom_graphid_id=str(self.graph_id)) & Q(
                    resourceinstanceto_graphid_id=resourceinstance_graphid
                )
                from_graph_id_filter = Q(resourceinstancefrom_graphid_id=resourceinstance_graphid) & Q(
                    resourceinstanceto_graphid_id=str(self.graph_id)
                )
                final_query = final_query & (to_graph_id_filter | from_graph_id_filter)

            relations = {
                "total": models.ResourceXResource.objects.filter(final_query).count(),
                "relations": models.ResourceXResource.objects.filter(final_query)[start:limit],
            }

            return relations  # resourceinstance_graphid = "00000000-886a-374a-94a5-984f10715e3a"

        resource_relations = get_relations(
            resourceinstanceid=self.resourceinstanceid,
            start=start,
            limit=limit,
            resourceinstance_graphid=resourceinstance_graphid,
        )


        resource_relations["relations"] = list(
            filter(lambda x: user_can_read_resource(user, x.resourceinstanceidto), resource_relations["relations"])
        )

        resource_relations["relations"] = list(
            filter(lambda x: user_can_read_resource(user, x.resourceinstanceidfrom), resource_relations["relations"])
        )

        resource_relations["total"] = len(resource_relations["relations"])
        ret["total"] = resource_relations["total"]

        instanceids = set()

        restricted_instances = get_restricted_instances(user, se) if user is not None else []
        for relation in resource_relations["relations"]:
            relation = model_to_dict(relation)
            try:
                preflabel = get_preflabel_from_valueid(relation["relationshiptype"], lang)
                relation["relationshiptype_label"] = preflabel["value"] or ""
            except:
                relation["relationshiptype_label"] = relation["relationshiptype"] or ""

            resourceid_to = relation["resourceinstanceidto"]
            resourceid_from = relation["resourceinstanceidfrom"]
            if resourceid_to not in restricted_instances and resourceid_from not in restricted_instances:
                ret["resource_relationships"].append(relation)
                instanceids.add(str(resourceid_to))
                instanceids.add(str(resourceid_from))
            else:
                ret["total"]["value"] -= 1

        if str(self.resourceinstanceid) in instanceids:
            instanceids.remove(str(self.resourceinstanceid))

        if len(instanceids) > 0:
            related_resources = se.search(index=RESOURCES_INDEX, id=list(instanceids))
            if related_resources:
                for resource in related_resources["docs"]:
                    relations = get_relations(
                        resourceinstanceid=resource["_id"],
                        start=0,
                        limit=0,
                    )
                    if resource["found"]:
                        resource["_source"]["total_relations"] = relations["total"]
                        ret["related_resources"].append(resource["_source"])

        return ret

    def copy(self):
        """
        Returns a copy of this resource instance including a copy of all tiles associated with this resource instance

        """
        # need this here to prevent a circular import error
        from arches.app.models.tile import Tile

        id_map = {}
        new_resource = Resource()
        new_resource.graph = self.graph

        if len(self.tiles) == 0:
            self.tiles = Tile.objects.filter(resourceinstance=self)

        for tile in self.tiles:
            new_tile = Tile()
            new_tile.data = tile.data
            new_tile.nodegroup = tile.nodegroup
            new_tile.parenttile = tile.parenttile
            new_tile.resourceinstance = new_resource
            new_tile.sortorder = tile.sortorder

            new_resource.tiles.append(new_tile)
            id_map[tile.pk] = new_tile

        for tile in new_resource.tiles:
            if tile.parenttile:
                tile.parenttile = id_map[tile.parenttile_id]

        with transaction.atomic():
            new_resource.save(context="copy")

        return new_resource

    def serialize(self, fields=None, exclude=None):
        """
        Serialize to a different form then used by the internal class structure

        used to append additional values (like parent ontology properties) that
        internal objects (like models.Nodes) don't support

        """

        ret = JSONSerializer().handle_model(self)
        ret["displayname"] = self.displayname()
        ret["tiles"] = self.tiles

        return JSONSerializer().serializeToPython(ret)

    def to_json(self, compact=True, hide_empty_nodes=False, user=None, perm=None, version=None, hide_hidden_nodes=False):
        """
        Returns resource represented as disambiguated JSON graph

        Keyword Arguments:
        compact -- type bool: hide superfluous node data
        hide_empty_nodes -- type bool: hide nodes without data
        """
        if version is None:
            return LabelBasedGraph.from_resource(
                resource=self, compact=compact, hide_empty_nodes=hide_empty_nodes, user=user, perm=perm, hide_hidden_nodes=hide_hidden_nodes
            )
        elif version == "beta":
            return LabelBasedGraphV2.from_resource(
                resource=self, compact=compact, hide_empty_nodes=hide_empty_nodes, user=user, perm=perm, hide_hidden_nodes=hide_hidden_nodes
            )

    @staticmethod
    def to_json__bulk(resources, compact=True, hide_empty_nodes=False, version=None):
        """
        Returns list of resources represented as disambiguated JSON graphs

        Keyword Arguments:
        resources -- list of Resource
        compact -- type bool: hide superfluous node data
        hide_empty_nodes -- type bool: hide nodes without data
        """

        if version is None:
            return LabelBasedGraph.from_resources(resources=resources, compact=compact, hide_empty_nodes=hide_empty_nodes)
        elif version == "beta":
            return LabelBasedGraphV2.from_resources(resources=resources, compact=compact, hide_empty_nodes=hide_empty_nodes)

    def get_node_values(self, node_name):
        """
        Take a node_name (string) as an argument and return a list of values.
        If an invalid node_name is used, or if multiple nodes with the same
        name are found, the method returns False.
        Current supported (tested) node types are: string, date, concept, geometry
        """

        nodes = models.Node.objects.filter(name=node_name, graph_id=self.graph_id)
        if len(nodes) > 1:
            raise MultipleNodesFoundException(node_name, nodes)

        if len(nodes) == 0:
            raise InvalidNodeNameException(node_name)

        tiles = self.tilemodel_set.filter(nodegroup_id=nodes[0].nodegroup_id)

        values = []
        for tile in tiles:
            for node_id, value in tile.data.items():
                if node_id == str(nodes[0].nodeid):
                    if type(value) is list:
                        for v in value:
                            values.append(parse_node_value(v))
                    else:
                        values.append(parse_node_value(value))

        return values

    def remove_resource_instance_permissions(self):
        groups = list(Group.objects.all())
        users = list(User.objects.all())
        for identity in groups + users:
            for perm in ["no_access_to_resourceinstance", "view_resourceinstance", "change_resourceinstance", "delete_resourceinstance"]:
                remove_perm(perm, identity, self)
        self.index()

    def add_permission_to_all(self, permission):
        groups = list(Group.objects.all())
        users = [user for user in User.objects.all() if user.is_superuser is False]
        for identity in groups + users:
            assign_perm(permission, identity, self)
        self.index()


def parse_node_value(value):
    if is_uuid(value):
        try:
            return models.Value.objects.get(pk=value).value
        except ObjectDoesNotExist:
            pass
    return value


def is_uuid(value_to_test):
    try:
        UUID(value_to_test)
        return True
    except Exception:
        return False


class ModelInactiveError(Exception):
    def __init__(self, message, code=None):
        self.title = _("Model Inactive Error")
        self.message = message
        self.code = code

    def __str__(self):
        return repr(self.message)

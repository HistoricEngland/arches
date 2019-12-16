import os
import re
import json
import uuid
import datetime
import logging
from io import StringIO
from django.urls import reverse
from .format import Writer, Reader
from arches.app.models import models
from arches.app.models.resource import Resource
from arches.app.models.graph import Graph as GraphProxy
from arches.app.models.tile import Tile
from arches.app.models.concept import Concept
from arches.app.models.system_settings import settings
from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.utils.data_management.resource_graphs.exporter import get_graphs_for_export
from rdflib import Namespace
from rdflib import URIRef, Literal
from rdflib import ConjunctiveGraph as Graph
from rdflib.namespace import RDF, RDFS
from pyld.jsonld import compact, frame, from_rdf, to_rdf, expand, set_document_loader


try:
    # If we have a context file in our working directory, load it
    fh = open("linked-art.json")
    context_data = fh.read()
    fh.close()

    def cached_context(url):
        return {"contextUrl": None, "documentUrl": "https://linked.art/ns/v1/linked-art.json", "document": context_data}

    set_document_loader(cached_context)
except:
    #  Guess we don't...
    pass


class RdfWriter(Writer):
    def __init__(self, **kwargs):
        self.format = kwargs.pop("format", "xml")
        self.logger = logging.getLogger(__name__)
        super(RdfWriter, self).__init__(**kwargs)

    def write_resources(self, graph_id=None, resourceinstanceids=None, **kwargs):
        super(RdfWriter, self).write_resources(graph_id=graph_id, resourceinstanceids=resourceinstanceids, **kwargs)

        dest = StringIO()
        g = self.get_rdf_graph()
        g.serialize(destination=dest, format=self.format)

        full_file_name = os.path.join("{0}.{1}".format(self.file_name, "rdf"))
        return [{"name": full_file_name, "outputfile": dest}]

    def get_rdf_graph(self):
        archesproject = Namespace(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT)
        graph_uri = URIRef(archesproject[reverse("graph", args=[self.graph_id]).lstrip("/")])
        self.logger.debug("Using `{0}` for Arches URI namespace".format(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT))
        self.logger.debug("Using `{0}` for Graph URI".format(graph_uri))

        g = Graph()
        g.bind("archesproject", archesproject, False)
        graph_cache = {}

        def get_nodegroup_edges_by_collector_node(node):
            edges = []
            nodegroup = node.nodegroup

            def getchildedges(node):
                for edge in models.Edge.objects.filter(domainnode=node):
                    if nodegroup == edge.rangenode.nodegroup:
                        edges.append(edge)
                        getchildedges(edge.rangenode)

            getchildedges(node)
            return edges

        def get_graph_parts(graphid):
            if graphid not in graph_cache:
                graph_cache[graphid] = {
                    "rootedges": [],
                    "subgraphs": {},
                    "nodedatatypes": {},
                }
                graph = models.GraphModel.objects.get(pk=graphid)
                nodegroups = set()
                for node in graph.node_set.all():
                    graph_cache[graphid]["nodedatatypes"][str(node.nodeid)] = node.datatype
                    if node.nodegroup:
                        nodegroups.add(node.nodegroup)
                    if node.istopnode:
                        for edge in get_nodegroup_edges_by_collector_node(node):
                            if edge.rangenode.nodegroup is None:
                                graph_cache[graphid]["rootedges"].append(edge)
                for nodegroup in nodegroups:
                    graph_cache[graphid]["subgraphs"][nodegroup] = {"edges": [], "inedge": None, "parentnode_nodegroup": None}
                    graph_cache[graphid]["subgraphs"][nodegroup]["inedge"] = models.Edge.objects.get(rangenode_id=nodegroup.pk)
                    graph_cache[graphid]["subgraphs"][nodegroup]["parentnode_nodegroup"] = graph_cache[graphid]["subgraphs"][nodegroup][
                        "inedge"
                    ].domainnode.nodegroup
                    graph_cache[graphid]["subgraphs"][nodegroup]["edges"] = get_nodegroup_edges_by_collector_node(
                        models.Node.objects.get(pk=nodegroup.pk)
                    )

            return graph_cache[graphid]

        def add_edge_to_graph(graph, domainnode, rangenode, edge, tile, graph_info):
            pkg = {}
            pkg["d_datatype"] = graph_info["nodedatatypes"].get(str(edge.domainnode.pk))
            dom_dt = self.datatype_factory.get_instance(pkg["d_datatype"])
            # Don't process any further if the domain datatype is a literal
            if dom_dt.is_a_literal_in_rdf():
                return

            pkg["r_datatype"] = graph_info["nodedatatypes"].get(str(edge.rangenode.pk))
            pkg["range_tile_data"] = None
            pkg["domain_tile_data"] = None
            if str(edge.rangenode_id) in tile.data:
                pkg["range_tile_data"] = tile.data[str(edge.rangenode_id)]
            if str(edge.domainnode_id) in tile.data:
                pkg["domain_tile_data"] = tile.data[str(edge.domainnode_id)]

            rng_dt = self.datatype_factory.get_instance(pkg["r_datatype"])
            pkg["d_uri"] = dom_dt.get_rdf_uri(domainnode, pkg["domain_tile_data"], "d")
            pkg["r_uri"] = rng_dt.get_rdf_uri(rangenode, pkg["range_tile_data"], "r")

            # Concept on a node that is not required, but not present
            # Nothing to do here
            if pkg["r_uri"] is None and pkg["range_tile_data"] is None:
                return

            # FIXME:  Why is this not in datatype.to_rdf()

            # Domain node is NOT a literal value in the RDF representation, so will have a type:
            if type(pkg["d_uri"]) == list:
                for duri in pkg["d_uri"]:
                    graph.add((duri, RDF.type, URIRef(edge.domainnode.ontologyclass)))
            else:
                graph.add((pkg["d_uri"], RDF.type, URIRef(edge.domainnode.ontologyclass)))

            # Use the range node's datatype.to_rdf() method to generate an RDF representation of it
            # and add its triples to the core graph

            # FIXME: some datatypes have their URI calculated from _tile_data (e.g. concept)
            # ... if there is a list of these, then all of the permutations will happen
            # ... as the matrix below re-processes all URIs against all _tile_data entries :(
            if type(pkg["d_uri"]) == list:
                mpkg = pkg.copy()
                for d in pkg["d_uri"]:
                    mpkg["d_uri"] = d
                    if type(pkg["r_uri"]) == list:
                        npkg = mpkg.copy()
                        for r in pkg["r_uri"]:
                            # compute matrix of n * m
                            npkg["r_uri"] = r
                            graph += rng_dt.to_rdf(npkg, edge)
                    else:
                        # iterate loop on m * 1
                        graph += rng_dt.to_rdf(mpkg, edge)
            elif type(pkg["r_uri"]) == list:
                npkg = pkg.copy()
                for r in pkg["r_uri"]:
                    # compute matrix of 1 * m
                    npkg["r_uri"] = r
                    graph += rng_dt.to_rdf(npkg, edge)
            else:
                # both are single, 1 * 1
                graph += rng_dt.to_rdf(pkg, edge)

        for resourceinstanceid, tiles in self.resourceinstances.items():
            graph_info = get_graph_parts(self.graph_id)

            # add the edges for the group of nodes that include the root (this group of nodes has no nodegroup)
            for edge in graph_cache[self.graph_id]["rootedges"]:
                domainnode = archesproject[str(edge.domainnode.pk)]
                rangenode = archesproject[str(edge.rangenode.pk)]
                add_edge_to_graph(g, domainnode, rangenode, edge, None, graph_info)

            for tile in tiles:
                # add all the edges for a given tile/nodegroup
                for edge in graph_info["subgraphs"][tile.nodegroup]["edges"]:
                    domainnode = archesproject["tile/%s/node/%s" % (str(tile.pk), str(edge.domainnode.pk))]
                    rangenode = archesproject["tile/%s/node/%s" % (str(tile.pk), str(edge.rangenode.pk))]
                    add_edge_to_graph(g, domainnode, rangenode, edge, tile, graph_info)

                # add the edge from the parent node to this tile's root node
                # where the tile has no parent tile, which means the domain node has no tile_id
                if graph_info["subgraphs"][tile.nodegroup]["parentnode_nodegroup"] is None:
                    edge = graph_info["subgraphs"][tile.nodegroup]["inedge"]
                    if edge.domainnode.istopnode:
                        domainnode = archesproject[reverse("resources", args=[resourceinstanceid]).lstrip("/")]
                    else:
                        domainnode = archesproject[str(edge.domainnode.pk)]
                    rangenode = archesproject["tile/%s/node/%s" % (str(tile.pk), str(edge.rangenode.pk))]
                    add_edge_to_graph(g, domainnode, rangenode, edge, tile, graph_info)

                # add the edge from the parent node to this tile's root node
                # where the tile has a parent tile
                if graph_info["subgraphs"][tile.nodegroup]["parentnode_nodegroup"] is not None:
                    edge = graph_info["subgraphs"][tile.nodegroup]["inedge"]
                    domainnode = archesproject["tile/%s/node/%s" % (str(tile.parenttile.pk), str(edge.domainnode.pk))]
                    rangenode = archesproject["tile/%s/node/%s" % (str(tile.pk), str(edge.rangenode.pk))]
                    add_edge_to_graph(g, domainnode, rangenode, edge, tile, graph_info)
        return g


class JsonLdWriter(RdfWriter):
    def write_resources(self, graph_id=None, resourceinstanceids=None, **kwargs):
        super(RdfWriter, self).write_resources(graph_id=graph_id, resourceinstanceids=resourceinstanceids, **kwargs)
        g = self.get_rdf_graph()
        value = g.serialize(format="nquads").decode("utf-8")

        # print(f"Got graph: {value}")
        js = from_rdf(value, {"format": "application/nquads", "useNativeTypes": True})

        assert len(resourceinstanceids) == 1  # currently, this should be limited to a single top resource

        archesproject = Namespace(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT)
        resource_inst_uri = archesproject[reverse("resources", args=[resourceinstanceids[0]]).lstrip("/")]

        context = self.graph_model.jsonldcontext
        framing = {"@omitDefault": True, "@omitGraph": False, "@id": str(resource_inst_uri)}

        if context:
            framing["@context"] = context

        js = frame(js, framing)

        try:
            context = JSONDeserializer().deserialize(context)
        except ValueError:
            if context == "":
                context = {}
            context = {"@context": context}
        except AttributeError:
            context = {"@context": {}}

        # Currently omitGraph is not processed by pyLd, but data is compacted
        # simulate omitGraph:
        if "@graph" in js and len(js["@graph"]) == 1:
            # merge up
            for (k, v) in list(js["@graph"][0].items()):
                js[k] = v
            del js["@graph"]

        out = json.dumps(js, indent=kwargs.get("indent", None), sort_keys=True)
        dest = StringIO(out)

        full_file_name = os.path.join("{0}.{1}".format(self.file_name, "jsonld"))
        return [{"name": full_file_name, "outputfile": dest}]


class JsonLdReader(Reader):
    def __init__(self):
        super(JsonLdReader, self).__init__()
        self.tiles = {}
        self.errors = {}
        self.resources = []
        self.resource = None
        self.use_ids = False
        self.resource_model_root_classes = set()
        self.non_unique_classes = set()
        self.graph_id_lookup = {}
        self.root_ontologyclass_lookup = {}
        self.jsonld_doc = None
        self.graphtree = None
        self.logger = logging.getLogger(__name__)
        for graph in models.GraphModel.objects.filter(isresource=True):
            node = models.Node.objects.get(graph_id=graph.pk, istopnode=True)
            self.graph_id_lookup[node.ontologyclass] = graph.pk
            self.root_ontologyclass_lookup[str(graph.pk)] = node.ontologyclass
            if node.ontologyclass in self.resource_model_root_classes:
                # make a note of non-unique root classes
                self.non_unique_classes.add(node.ontologyclass)
            else:
                self.resource_model_root_classes.add(node.ontologyclass)
        self.resource_model_root_classes = self.resource_model_root_classes - self.non_unique_classes
        self.ontologyproperties = models.Edge.objects.values_list("ontologyproperty", flat=True).distinct()
        self.logger.info("Initialized JsonLdReader")
        self.logger.debug("Found {0} Non-unique root classes".format(len(self.non_unique_classes)))
        self.logger.debug("Found {0} Resource Model Root classes".format(len(self.resource_model_root_classes)))

    def validate_concept_in_collection(self, value, collection):
        cdata = Concept().get_child_collections(collection, columns="conceptidto")
        ids = [str(x[0]) for x in cdata]
        for c in cdata:
            cids = [x.value for x in models.Value.objects.all().filter(concept_id__exact=c[0], valuetype__category="identifiers")]
            ids.extend(cids)
        if value.startswith(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT):
            value = value.rsplit("/", 1)[-1]
        return str(value) in ids

    def process_graph(self, graphid):
        root_node = None
        nodes = {}
        graph = GraphProxy.objects.get(graphid=graphid)
        for nodeid, n in graph.nodes.items():
            node = {}
            if n.istopnode:
                root_node = node
            node["datatype"] = self.datatype_factory.get_instance(n.datatype)
            node["datatype_type"] = n.datatype
            node["extra_class"] = []
            if n.datatype in ["resource-instance", "resource-instance-list"]:
                if "graphid" in n.config and n.config["graphid"]:
                    graph_ids = n.config["graphid"]
                    for gid in graph_ids:
                        node["extra_class"].append(self.root_ontologyclass_lookup[gid])

            node["config"] = {}
            if n.config and "rdmCollection" in n.config:
                node["config"]["collection_id"] = str(n.config["rdmCollection"])
            node["required"] = n.isrequired
            node["node_id"] = str(n.nodeid)
            node["name"] = n.name
            node["class"] = n.ontologyclass
            node["nodegroup_id"] = str(n.nodegroup_id)
            node["cardinality"] = n.nodegroup.cardinality if n.nodegroup else None
            node["out_edges"] = []
            node["children"] = {}
            nodes[str(n.nodeid)] = node

        for edegid, e in graph.edges.items():
            dn = e.domainnode_id
            rng = e.rangenode_id
            prop = e.ontologyproperty
            nodes[str(dn)]["out_edges"].append({"range": str(rng), "prop": str(prop)})

        def model_walk(node, nodes):
            for e in node["out_edges"]:
                rng = nodes[e["range"]]
                for oclass in set([rng["class"], *rng["extra_class"]]):
                    key = f"{e['prop']} {oclass}"
                    if key in node["children"]:
                        node["children"][key].append(rng)
                    else:
                        node["children"][key] = [rng]
                model_walk(rng, nodes)
            del node["out_edges"]

        model_walk(root_node, nodes)

        # tree now represents a concise description of the structure of the model
        # print(json.dumps(root_node, indent=4))
        return root_node

    def get_resource_id(self, value):
        # Allow local URI or urn:uuid:UUID
        # print("In get_resource_id")
        match = re.match(r".*?%sresources/(?P<resourceid>%s)" % (settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT, settings.UUID_REGEX), value)
        if match:
            return match.group("resourceid")
        else:
            match = re.match(r"urn:uuid:(%s)" % settings.UUID_REGEX, value)
            if match:
                return match.groups()[0]
            else:
                self.logger.debug("Valid resourceid not found within `{0}`".format(value))
        return None

    def read_resource(self, data, use_ids=False, resourceid=None, graphid=None):
        self.use_ids = use_ids
        if not isinstance(data, list):
            data = [data]

        for jsonld_document in data:
            self.errors = {}
            jsonld_document = expand(jsonld_document)[0]
            # print(jsonld_document)
            if graphid is None:
                graphid = self.get_graph_id(jsonld_document["@type"][0])
                self.logger.debug("graphid is not set. Using the @type value instead: {0}".format(jsonld_document["@type"][0]))
            if graphid:
                if use_ids == True:
                    resourceinstanceid = self.get_resource_id(jsonld["@id"])
                    if resourceinstanceid is None:
                        self.logger.error("The @id of the resource was not supplied, was null or URI was not correctly formatted")
                        raise Exception("The @id of the resource was not supplied, was null or URI was not correctly formatted")
                    self.logger.debug("Resource instance ID found: {0}".format(resourceinstanceid))
                    self.resource = Resource.objects.get(pk=resourceinstanceid)
                else:
                    self.logger.debug("`use_ids` setting is set to False, creating new Resource Instance IDs on import")
                    self.resource = Resource()
                    self.resource.graph_id = graphid
                    self.resource.pk = resourceid
                self.resources.append(self.resource)

            tree = self.process_graph(graphid)

            ### --- Process Instance ---
            # now walk the instance and align to the tree
            # first check @type of the instance against the model
            if jsonld_document["@type"][0] != tree["class"]:
                raise ValueError("Instance does not have same top level class as model")

            result = {"data": [jsonld_document["@id"]]}
            self.data_walk(jsonld_document, tree, result)
            # print(JSONSerializer().serialize(result, indent=4))

    def is_semantic_node(self, graph_node):
        return self.datatype_factory.datatypes[graph_node["datatype_type"]].defaultwidget is None

    def is_resource_instance_node(self, graph_node, uri):
        return (
            uri.startswith("urn:uuid:") or uri.startswith(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT + "resources/")
        ) and not self.is_semantic_node(graph_node)

    def is_concept_node(self, uri):
        pcs = settings.PREFERRED_CONCEPT_SCHEMES[:]
        pcs.append(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT + "concepts/")
        for p in pcs:
            if uri.startswith(p):
                return True
        return False

    def data_walk(self, data_node, tree_node, result, tile=None):
        for k, v in data_node.items():
            if k in ["@id", "@type"]:
                continue
            # always a list
            for vi in v:
                if "@value" in vi:
                    # We're a literal value
                    value = vi["@value"]
                    clss = vi.get("@type", "http://www.w3.org/2000/01/rdf-schema#Literal")
                    uri = None
                    is_literal = True
                else:
                    # We're an entity
                    uri = vi.get("@id", "")
                    try:
                        clss = vi["@type"][0]
                    except:
                        # {"@id": "http://something/.../"}
                        # with no @type. This is typically an external concept URI
                        # Look for it in the children of current node
                        possible_cls = []
                        for tn in tree_node["children"]:
                            if tn.startswith(k):
                                possible_cls.append(tn.replace(k, "")[1:])
                        if len(possible_cls) == 1:
                            clss = possible_cls[0]
                        else:
                            raise ValueError(f"Multiple possible branches and no @type given: {vi}")

                    value = None
                    is_literal = False

                # Find precomputed possible branches by prop/class combination
                key = f"{k} {clss}"
                if key in tree_node["datatype"].ignore_keys():
                    # these are handled by the datatype itself
                    continue
                elif not key in tree_node["children"] and is_literal:
                    # grumble grumble
                    # model has xsd:string, default is rdfs:Literal
                    key = f"{k} http://www.w3.org/2001/XMLSchema#string"
                    if not key in tree_node["children"]:
                        raise ValueError(f"property/class combination does not exist in model: {k} {clss}")
                elif not key in tree_node["children"]:
                    raise ValueError(f"property/class combination does not exist in model: {k} {clss}")

                options = tree_node["children"][key]
                possible = []
                ignore = []
                # print(f"\nConsidering {len(options)} options ...")
                for o in options:
                    # print(f"Considering:\n  {vi}\n  {o}")
                    if is_literal and o["datatype"].is_a_literal_in_rdf():
                        if len(o["datatype"].validate(value)) == 0:
                            possible.append([o, value])
                        else:
                            print(f"Could not validate {value} as a {o['datatype']}")
                    elif not is_literal and not o["datatype"].is_a_literal_in_rdf():
                        if self.is_concept_node(uri):
                            collid = o["config"]["collection_id"]
                            if self.validate_concept_in_collection(uri, collid):
                                possible.append([o, uri])
                            else:
                                print(f"Concept URI {uri} not in Collection {collid}")
                        elif self.is_resource_instance_node(o, uri):
                            possible.append([o, uri])
                        elif self.is_semantic_node(o):
                            possible.append([o, ""])
                        else:
                            # This is when the current option doesn't match, but could be
                            # non-ambiguous resource-instance vs semantic node
                            continue
                    else:
                        raise ValueError("No possible match?")

                if not possible:
                    raise ValueError(f"Data does not match any actual node, despite prop/class combination {k} {clss}:\n{vi}")
                elif len(possible) > 1:
                    # descend into data to check if there are further clarifying features
                    possible2 = []
                    for p in possible:
                        try:
                            # Don't really create data, so pass anonymous result dict
                            self.data_walk(vi, p[0], {}, tile)
                            possible2.append(p)
                        except:
                            # Not an option
                            pass
                    if not possible2:
                        raise ValueError("Considering branches, data does not match any node, despite a prop/class combination")
                    elif len(possible2) > 1:
                        raise ValueError("Even after considering branches, data still matches more than one node")
                    else:
                        branch = possible2[0]
                else:
                    branch = possible[0]

                if not self.is_semantic_node(branch[0]):
                    graph_node = branch[0]
                    # import ipdb
                    # ipdb.sset_trace()
                    node_value = graph_node["datatype"].from_rdf(vi)

                # We know now that it can go into the branch
                # Determine if we can collapse the data into a -list or not
                bnodeid = branch[0]["node_id"]
                # bnodeid = f"{branch[0]['node_id']}/{branch[0]['name']}"
                create_new_tile = False

                if branch[0]["node_id"] == branch[0]["nodegroup_id"]:
                    create_new_tile = True
                bnode = {"data": [], "nodegroup_id": branch[0]["nodegroup_id"], "cardinality": branch[0]["cardinality"]}
                if create_new_tile:
                    parenttile_id = tile.tileid if tile else None
                    tile = Tile(tileid=uuid.uuid4(), parenttile_id=parenttile_id, nodegroup_id=branch[0]["nodegroup_id"], data={})
                    self.resource.tiles.append(tile)

                bnode["tile"] = tile

                if bnodeid in result:
                    if branch[0]["datatype"].collects_multiple_values():
                        # append to previous tile
                        if type(node_value) != list:
                            node_value = [node_value]
                        bnode = result[bnodeid][0]
                        bnode["data"].append(branch[1])
                        if not self.is_semantic_node(branch[0]):
                            try:
                                n = bnode["tile"].data[bnodeid]
                            except:
                                n = []
                                bnode["tile"].data[bnodeid] = n
                            if type(n) != list:
                                bnode["tile"].data[bnodeid] = [n]
                            bnode["tile"].data[bnodeid].extend(node_value)
                    elif branch[0]["cardinality"] != "n":
                        raise ValueError("Attempt to add a value to cardinality 1, non-list node")
                    else:
                        bnode["data"].append(branch[1])
                        if not self.is_semantic_node(branch[0]):
                            print(f"Adding to existing (n): {node_value}")
                            tile.data[bnodeid] = node_value
                        result[bnodeid].append(bnode)
                else:
                    if not self.is_semantic_node(branch[0]):
                        # FIXME: This is clearly broken
                        if branch[0]["datatype"].collects_multiple_values() and tile is not None:
                            tile.data[bnodeid] = node_value
                        else:
                            tile.data[bnodeid] = node_value
                    bnode["data"].append(branch[1])
                    result[bnodeid] = [bnode]

                if not is_literal:
                    # Walk down non-literal branches in the data
                    self.data_walk(vi, branch[0], bnode, tile)

        # Finally, after processing all of the branches for this node, check required nodes are present
        for path in tree_node["children"].values():
            for kid in path:
                if kid["required"] and not f"{kid['node_id']}" in result:
                    raise ValueError("Required field not present")


# class JsonLdReader(Reader):
#     def __init__(self):
#         super(JsonLdReader, self).__init__()
#         self.tiles = {}
#         self.errors = {}
#         self.resources = []
#         self.use_ids = False
#         self.resource_model_root_classes = set()
#         self.non_unique_classes = set()
#         self.graph_id_lookup = {}
#         self.root_ontologyclass_lookup = {}
#         self.jsonld_doc = None
#         self.graphtree = None
#         self.logger = logging.getLogger(__name__)
#         for graph in models.GraphModel.objects.filter(isresource=True):
#             node = models.Node.objects.get(graph_id=graph.pk, istopnode=True)
#             self.graph_id_lookup[node.ontologyclass] = graph.pk
#             self.root_ontologyclass_lookup[str(graph.pk)] = node.ontologyclass
#             if node.ontologyclass in self.resource_model_root_classes:
#                 # make a note of non-unique root classes
#                 self.non_unique_classes.add(node.ontologyclass)
#             else:
#                 self.resource_model_root_classes.add(node.ontologyclass)
#         self.resource_model_root_classes = self.resource_model_root_classes - self.non_unique_classes
#         self.ontologyproperties = models.Edge.objects.values_list("ontologyproperty", flat=True).distinct()
#         self.logger.info("Initialized JsonLdReader")
#         self.logger.debug("Found {0} Non-unique root classes".format(len(self.non_unique_classes)))
#         self.logger.debug("Found {0} Resource Model Root classes".format(len(self.resource_model_root_classes)))
#         # self.logger.debug("Resource Model Root classes: {0}".format("\n".join(list(map(str, self.resource_model_root_classes)))))

#     def get_graph_id(self, root_ontologyclass):
#         if root_ontologyclass in self.resource_model_root_classes:
#             return self.graph_id_lookup[root_ontologyclass]
#         else:
#             self.logger.info(
#                 "Incoming Root Ontology class `{0}` not found within the list of Resource Model Root Classes".format(root_ontologyclass)
#             )
#         return None

#     def get_resource_id(self, value):
#         # Allow local URI or urn:uuid:UUID
#         print("In get_resource_id")
#         match = re.match(r".*?%sresources/(?P<resourceid>%s)" % (settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT, settings.UUID_REGEX), value)
#         if match:
#             return match.group("resourceid")
#         else:
#             match = re.match(r"urn:uuid:(%s)" % settings.UUID_REGEX, value)
#             if match:
#                 return match.groups()[0]
#             else:
#                 self.logger.debug("Valid resourceid not found within `{0}`".format(value))
#         return None

#     def read_resource(self, data, use_ids=False, resourceid=None, graphid=None):
#         self.use_ids = use_ids
#         if not isinstance(data, list):
#             data = [data]

#         for jsonld in data:
#             self.errors = {}
#             # FIXME: This should use a cache of the context
#             jsonld = expand(jsonld)[0]
#             print(jsonld)
#             self.jsonld_doc = jsonld
#             if graphid is None:
#                 graphid = self.get_graph_id(jsonld["@type"][0])
#                 self.logger.debug("graphid is not set. Using the @type value instead: {0}".format(jsonld["@type"][0]))
#             if graphid:
#                 graph = GraphProxy.objects.get(graphid=graphid)
#                 self.graphtree = graph.get_tree()
#                 if use_ids == True:
#                     resourceinstanceid = self.get_resource_id(jsonld["@id"])
#                     if resourceinstanceid is None:
#                         self.logger.error("The @id of the resource was not supplied, was null or URI was not correctly formatted")
#                         raise Exception("The @id of the resource was not supplied, was null or URI was not correctly formatted")
#                     self.logger.debug("Resource instance ID found: {0}".format(resourceinstanceid))
#                     resource = Resource.objects.get(pk=resourceinstanceid)
#                 else:
#                     self.logger.debug("`use_ids` setting is set to False, creating new Resource Instance IDs on import")
#                     resource = Resource()
#                     resource.graph_id = graphid
#                     resource.pk = resourceid

#                 self.add_node_ids(jsonld)
#                 try:
#                     self.resolve_jsonld_doc(resource)
#                     self.resources.append(resource)
#                 except self.DataDoesNotMatchGraphException as e:
#                     self.logger.error("Mismatch when trying to match the JSON LD section with a relevant Arches Branch")
#                     self.logger.debug(e.message)
#                     self.errors["DataDoesNotMatchGraphException"] = e
#                 except self.AmbiguousGraphException as e:
#                     self.logger.error("Ambiguous Graph exception thrown")
#                     self.logger.debug(e.message)
#                     self.errors["AmbiguousGraphException"] = e

#         return data

#     class AmbiguousGraphException(Exception):
#         def __init__(self):
#             self.message = "The target graph is ambiguous, please supply node ids in the jsonld to disabmiguate."

#     class DataDoesNotMatchGraphException(Exception):
#         def __init__(self):
#             self.message = "A node in the supplied data does not match any node in the target graph. "

#     def findOntologyProperties(self, o):
#         keys = []
#         try:
#             for key in list(o.keys()):
#                 if key in self.ontologyproperties:
#                     keys.append(key)
#         except:
#             pass
#         # self.logger.debug("    findOntologyProperties -> {0}".format("\n".join(map(str, keys))))
#         return keys

#     def resolve_jsonld_doc(self, resource):
#         graph_paths = self.get_paths(self.graphtree)
#         jsonld_paths = self.get_jsonld_paths(self.jsonld_doc)
#         self.logger.debug(f"Graph Paths: {self.path_to_string(graph_paths)}")
#         self.logger.debug(f"JSONLD Doc Paths: {self.path_to_string(jsonld_paths)}")

#         depth = None  # how deeply nested is the jsonld node in jsonld document
#         found_jsonld_paths = []

#         def fgp_to_str(fgp):
#             return "/".join([x["label"][x["label"].rfind("/") + 1 :] for x in fgp])

#         for jsonld_path in jsonld_paths:

#             found_graph_paths = []
#             # here we find the graph paths that share the same pattern as the jsonld paths identified above
#             # the found graph path don't take into consideration the node ids (only ontologyclass and ontologyproperty sequence)
#             for jsonld_path_str in self.path_to_string([jsonld_path]):
#                 for graph_path in graph_paths:
#                     if self.path_to_string([graph_path])[0].startswith(jsonld_path_str):
#                         found_graph_paths.append(graph_path)

#             if len(found_graph_paths) > 1:
#                 self.logger.debug(
#                     f"More than one path in graph: {self.path_to_string(found_graph_paths)}\
#                     -- Now trying to differentiate"
#                 )
#                 graph_paths_to_remove = set()
#                 for i, jsonld_node in enumerate(jsonld_path):
#                     if i % 2 == 0:
#                         # if str(RDFS.label) in jsonld_node["jsonld_node"] and "@value" in jsonld_node["jsonld_node"][str(RDFS.label)][0]:
#                         if "@id" in jsonld_node["jsonld_node"] and (
#                             jsonld_node["jsonld_node"]["@id"].startswith(settings.PREFERRED_CONCEPT_SCHEME)
#                             or jsonld_node["jsonld_node"]["@id"].startswith(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT + "concepts/")
#                         ):
#                             self.logger.debug(f"Testing for concept: {jsonld_node['jsonld_node']['@id']}")
#                             for path_id, found_graph_path in enumerate(found_graph_paths):
#                                 if (
#                                     found_graph_path[i]["node"]["node"].datatype == "concept"
#                                     or found_graph_path[i]["node"]["node"].datatype == "concept-list"
#                                 ):
#                                     concept_node = found_graph_path[i]["node"]
#                                     collection = concept_node["node"].config["rdmCollection"]
#                                     edges = Concept().get_child_collections(collection, columns="valueto")
#                                     concept_labels = [item[0] for item in edges]

#                                     all_values_found = True
#                                     for concept_val in jsonld_node["jsonld_node"][str(RDFS.label)]:
#                                         if concept_val["@value"] not in concept_labels:
#                                             all_values_found = False

#                                     if not all_values_found:
#                                         graph_paths_to_remove.add(path_id)
#                         elif (
#                             "@id" in jsonld_node["jsonld_node"]
#                             and jsonld_node["jsonld_node"]["@id"].startswith(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT + "resources/")
#                             and "@id" in self.jsonld_doc
#                             and jsonld_node["jsonld_node"]["@id"] != self.jsonld_doc["@id"]
#                         ):
#                             # This can only be the top node, a resource-instance or resource-instance-list
#                             # self.logger.debug(f"Testing for resource-instance: {jsonld_node}")
#                             for path_id, found_graph_path in enumerate(found_graph_paths):
#                                 # print(f"found_graph_path:\n{found_graph_path}\njsonld_node:\n{jsonld_node}")
#                                 if found_graph_path[i]["node"]["node"].datatype in ["resource-instance", "resource-instance-list"]:
#                                     self.logger.debug(f"Found res-inst path: {found_graph_path[i]['node']}")
#                                     pass
#                                 else:
#                                     self.logger.debug(f"Removing path: {fgp_to_str(found_graph_path)}")
#                                     graph_paths_to_remove.add(path_id)

#                 for i in sorted(graph_paths_to_remove, reverse=True):
#                     del found_graph_paths[i]

#             if len(found_graph_paths) == 0:
#                 raise self.DataDoesNotMatchGraphException()
#             elif len(found_graph_paths) == 1:
#                 # we've found our path in the graph, now we just need to populate the tiles
#                 self.logger.debug(
#                     f"Found a path in the graph ({self.path_to_string(found_graph_paths)[0]}) that matches a path in the json ld document ({self.path_to_string([jsonld_path])})"
#                 )
#                 self.assign_tiles(found_graph_paths[0], jsonld_path, resource)
#             elif len(found_graph_paths) > 1:
#                 self.logger.debug(f"Found matches: {[self.path_to_string(x) for x in found_graph_paths]}")
#                 raise self.AmbiguousGraphException()

#         # print(JSONSerializer().serialize(self.tiles))
#         return None

#     def add_node_ids(self, jsonld_graph):
#         from random import random

#         def graph_to_paths(jsonld_node):
#             jsonld_node["_id"] = random()
#             property_nodes = self.findOntologyProperties(jsonld_node)
#             if len(property_nodes) > 0:
#                 for property_node in property_nodes:
#                     if isinstance(jsonld_node[property_node], list):
#                         for node in jsonld_node[property_node]:
#                             ret = graph_to_paths(node)
#             return

#         return graph_to_paths(jsonld_graph)

#     def assign_tiles(self, graph_path, jsonld_path, resource):
#         # we've found our path in the graph, now we just need to populate the tiles

#         # import ipdb

#         # ipdb.sset_trace()
#         for i, jsonld_node in enumerate(jsonld_path):
#             if i % 2 == 0:
#                 # jsonld_node["node"] = graph_path[i]["node"]["node"].name
#                 parent_node = None if i < 2 else graph_path[i - 2]["node"]
#                 if parent_node is not None:
#                     self.add_tile(jsonld_node, graph_path[i]["node"], parent_node, resource)

#     def add_tile(self, jsonld_node, current_node, parent_node, resource):
#         datatype = self.datatype_factory.get_instance(current_node["node"].datatype)
#         tileid = current_node.get("tileid", None)
#         # if the node already has data attached to it then we need to make a new tile
#         # if the card allows it (cardinality == "n")
#         # it would be nice to know if a datatype supported lists of things
#         # if tileid and self.tiles[tileid].data[str(current_node["node"].nodeid)] and current_node["node"].nodegroup.cardinality == "n":
#         #     tileid = None
#         existing_value = None
#         if tileid is not None and str(current_node["node"].nodeid) in self.tiles[tileid].data:
#             existing_value = self.tiles[tileid].data[str(current_node["node"].nodeid)]
#         if (
#             datatype.collects_multiple_values() is False
#             and existing_value is not None
#             and current_node["node"].nodegroup.cardinality == "n"
#         ):
#             tileid = None
#         # else:
#         #     # if we get here something is wrong
#         #     raise Exception("Uh oh!")
#         #     pass

#         if self.use_ids:
#             try:
#                 match = re.match(
#                     r".*?/tile/(?P<tileid>%s)/node/(?P<nodeid>%s)" % (settings.UUID_REGEX, settings.UUID_REGEX), str(jsonld_node["@id"]),
#                 )
#                 if match:
#                     tileid = match.group("tileid")
#                     self.logger.debug("Found matching tile id `{0}` from the tile/node URI".format(tileid))
#             except:
#                 pass

#         else:
#             if tileid is None:
#                 if current_node["node"].nodegroup != parent_node["node"].nodegroup:
#                     tileid = uuid.uuid4()
#                 else:
#                     tileid = parent_node["tileid"]

#         if tileid is None:
#             raise Exception("A tileid couldn't be derived.  That's a problem.")

#         current_node["tileid"] = tileid

#         if tileid not in self.tiles:
#             self.logger.debug("Target tileid does not exist - creating {0}".format(tileid))

#             # !! this might be wrong the way we calculate the parent tile id---
#             self.tiles[tileid] = Tile(
#                 tileid=tileid, parenttile_id=parent_node["tileid"], nodegroup_id=current_node["node"].nodegroup_id, data={}
#             )
#             if parent_node["tileid"] is None:
#                 self.logger.debug("Tile does not have a parent tileid - adding to resource.tiles list")
#                 resource.tiles.append(self.tiles[tileid])
#             else:
#                 self.logger.debug("Tile does has {0} as parent tileid".format(parent_node["tileid"]))
#                 self.tiles[parent_node["tileid"]].tiles.append(self.tiles[tileid])

#         if self.datatype_factory.datatypes[current_node["node"].datatype].defaultwidget is not None:
#             self.logger.debug("Assigning value to datatype ({0}) from a non-semantic node:".format(current_node["node"].datatype))
#             value = datatype.from_rdf(jsonld_node["jsonld_node"])

#             self.logger.debug("value found! : {0}".format(value))

#             # if the tile already has a value for the given nodeid
#             if str(current_node["node"].nodeid) in self.tiles[tileid].data:
#                 # import ipdb

#                 # ipdb.sset_trace()
#                 existing_value = self.tiles[tileid].data[str(current_node["node"].nodeid)]
#                 # if current_node["node"].nodegroup.cardinality == "n":
#                 #     self.add_tile(jsonld_node, graph_path[i]["node"], parent_node, resource)
#                 # else:
#                 if not isinstance(existing_value, list):
#                     existing_value = [existing_value]
#                 if not isinstance(value, list):
#                     value = [value]
#                 value = value + existing_value
#                 self.tiles[tileid].data[str(current_node["node"].nodeid)] = value
#             else:
#                 self.tiles[tileid].data[str(current_node["node"].nodeid)] = value

#         return tileid

#     def get_paths(self, graphtree):
#         def graph_to_paths(current_node, path=[], path_list=[]):
#             if len(path) == 0:
#                 current_path = []
#             else:
#                 current_path = path[:]

#             current_node["tileid"] = None
#             if current_node["parent_edge"] is not None:
#                 current_path.append({"label": current_node["parent_edge"].ontologyproperty, "node": current_node},)
#                 current_path.append({"label": current_node["node"].ontologyclass, "node": current_node},)
#             else:
#                 current_path.append({"label": current_node["node"].ontologyclass, "node": current_node},)

#             if len(current_node["children"]) == 0:
#                 path_list.append(current_path[:])
#             else:
#                 for node in current_node["children"]:
#                     if node["node"].datatype == "resource-instance":
#                         for graphid in node["node"].config["graphid"]:
#                             node["node"].ontologyclass = self.root_ontologyclass_lookup[graphid]
#                             ret = graph_to_paths(node, current_path, path_list)
#                     else:
#                         ret = graph_to_paths(node, current_path, path_list)

#             return path_list

#         return graph_to_paths(graphtree)

#     def strip(self, url):
#         return url.split("/")[-1]

#     def get_jsonld_paths(self, jsonld):
#         # "p2_classified_as/E55_Type": [{
#         #     "datatype": "concept-list",
#         #     "cardinality": 1,
#         #     "is_literal": True,
#         #     "is_list_type": True
#         #     "children": {}
#         # }],
#         self.jsonld_tree = {}

#         self.first_iteration = True

#         def graph_to_paths(
#             jsonld_node, path=[], ontologyclass=None, property_class=None, previous_node=None, path_list=[], jsonld_tree=dict()
#         ):
#             current_path = path[:]
#             if ontologyclass is not None:
#                 current_path.append({"label": ontologyclass, "_id": previous_node["_id"], "jsonld_node": previous_node},)
#             if property_class is not None:
#                 current_path.append({"label": property_class},)

#             property_classes = self.findOntologyProperties(jsonld_node)
#             if "@type" in jsonld_node:
#                 ontologyclass = jsonld_node["@type"][0] if isinstance(jsonld_node["@type"], list) else jsonld_node["@type"]
#             else:
#                 ontologyclass = str(RDFS.Literal)

#             if ontologyclass is not None and property_class is not None:
#                 self.first_iteration = False
#                 jsonld_tree[f"{self.strip(property_class)}/{self.strip(ontologyclass)}"] = []

#             prev_property_class = property_class

#             if len(property_classes) > 0:
#                 for property_class in property_classes:
#                     if isinstance(jsonld_node[property_class], list):
#                         for node in jsonld_node[property_class]:
#                             child = {}
#                             if not self.first_iteration:
#                                 print(f"{self.strip(prev_property_class)}/{self.strip(ontologyclass)}")
#                                 jsonld_tree[f"{self.strip(prev_property_class)}/{self.strip(ontologyclass)}"].append({"children": child})
#                             else:
#                                 child = jsonld_tree
#                             ret = graph_to_paths(node, current_path, ontologyclass, property_class, jsonld_node, path_list, child,)
#             else:
#                 self.first_iteration = True
#                 current_path.append({"label": ontologyclass, "_id": jsonld_node["_id"], "jsonld_node": jsonld_node},)
#                 path_list.append(current_path[:])

#             return path_list

#         import ipdb

#         # ipdb.sset_trace()
#         x = graph_to_paths(jsonld, jsonld_tree=self.jsonld_tree)
#         print("-" * 30)
#         print(self.jsonld_tree)

#         return x

#     def path_to_string(self, pathlists):
#         ret = []
#         for pathlist in pathlists:
#             pathstr = []
#             for path in pathlist:
#                 pathstr.append(path["label"].split("/")[-1])
#             ret.append(",".join(pathstr))
#         return ret

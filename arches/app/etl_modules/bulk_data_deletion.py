from datetime import datetime
import json
import logging
import uuid
from django.contrib.auth.models import User
from django.db import connection
from django.http import HttpRequest
from django.utils.translation import gettext as _
from arches.app.etl_modules.base_data_editor import BaseBulkEditor
from arches.app.etl_modules.decorators import load_data_async
from arches.app.models.resource import Resource
from arches.app.models.system_settings import settings
from arches.app.models.tile import Tile
import arches.app.tasks as tasks
from arches.app.utils.index_database import index_resources_by_transaction

logger = logging.getLogger(__name__)



class BulkDataDeletion(BaseBulkEditor):
    def write(self, request):
        graph_id = request.POST.get("graph_id", None)
        graph_name = request.POST.get("graph_name", None)
        nodegroup_id = request.POST.get("nodegroup_id", None)
        nodegroup_name = request.POST.get("nodegroup_name", None)
        resourceids = request.POST.get("resourceids", None)
        search_url = request.POST.get("search_url", None)

        if resourceids:
            resourceids = json.loads(resourceids)
        if resourceids:
            resourceids = tuple(resourceids)
        if search_url:
            resourceids = self.get_resourceids_from_search_url(search_url)

        use_celery_bulk_delete = True

        load_details = {
            "graph": graph_name,
            "nodegroup": nodegroup_name,
            "search_url": search_url,
        }

        with connection.cursor() as cursor:
            event_created = self.create_load_event(cursor, load_details)
            if event_created["success"]:
                if use_celery_bulk_delete:
                    response = self.run_load_task_async(request, self.loadid)
                else:
                    response = self.run_load_task(self.userid, self.loadid, self.moduleid, graph_id, nodegroup_id, resourceids)
            else:
                self.log_event(cursor, "failed")
                return {"success": False, "data": event_created["message"]}

        return response

    @load_data_async
    def run_load_task_async(self, request):
        graph_id = request.POST.get("graph_id", None)
        nodegroup_id = request.POST.get("nodegroup_id", None)
        resourceids = request.POST.get("resourceids", None)
        search_url = request.POST.get("search_url", None)

        if resourceids:
            resourceids = json.loads(resourceids)
        if search_url:
            resourceids = self.get_resourceids_from_search_url(search_url)

        edit_task = tasks.bulk_data_deletion.apply_async(
            (self.userid, self.loadid, graph_id, nodegroup_id, resourceids),
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE load_event SET taskid = %s WHERE loadid = %s""",
                (edit_task.task_id, self.loadid),
            )

    def run_load_task(self, userid, loadid, graph_id, nodegroup_id, resourceids):
        if resourceids:
            resourceids = [uuid.UUID(id) for id in resourceids]

        if nodegroup_id:
            deleted = self.delete_tiles(userid, loadid, nodegroup_id, resourceids)
        elif graph_id:
            deleted = self.delete_resources(userid, loadid, graph_id, resourceids)

        if deleted["success"]:
            with connection.cursor() as cursor:
                self.log_event(cursor, "completed")
        else:
            with connection.cursor() as cursor:
                self.log_event(cursor, "failed")
            return {"success": False, "data": {"title": _("Error"), "message": deleted["message"]}}

        try:
            index_resources_by_transaction(loadid, quiet=True, use_multiprocessing=False, recalculate_descriptors=True)            
        except Exception as e:
            logger.exception(e)
            with connection.cursor() as cursor:
                self.log_event(cursor, "unindexed")
            
            return {"success": False, "data": {"title": _("Indexing Error"), "message": _("The database may need to be reindexed. Please contact your administrator.")}}

        cursor.execute(
            """UPDATE load_event SET (status, indexed_time, complete, successful) = (%s, %s, %s, %s) WHERE loadid = %s""",
            ("indexed", datetime.now(), True, True, loadid),
        )
        return {"success": True, "data": "indexed"}

    def delete_resources(self, userid, loadid, graphid, resourceids):
        result = {"success": False}
        user = User.objects.get(id=userid)
        try:
            if resourceids:
                resources = Resource.objects.filter(graph_id=graphid).filter(pk__in=resourceids)
            else:
                resources = Resource.objects.filter(graph_id=graphid)
            for resource in resources.iterator():
                resource.delete(user=user, index=False, transaction_id=loadid)
            result["success"] = True
        except Exception as e:
            logger.exception(e)
            result["message"] = _("Unable to delete resources: {}").format(str(e))

        return result

    def delete_tiles(self, userid, loadid, nodegroupid, resourceids):
        result = {"success": False}
        user = User.objects.get(id=userid)

        try:
            if resourceids:
                tiles = Tile.objects.filter(nodegroup_id=nodegroupid).filter(resourceinstance_id__in=resourceids)
            else:
                tiles = Tile.objects.filter(nodegroup_id=nodegroupid)
            for tile in tiles.iterator():
                request = HttpRequest()
                request.user = user
                tile.delete(request=request, index=False, transaction_id=loadid)
            result["success"] = True
        except Exception as e:
            logger.exception(e)
            result["message"] = _("Unable to delete tiles: {}").format(str(e))

        return result

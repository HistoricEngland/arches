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

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os
from arches.app.datatypes import url
from tests import test_settings
from tests.base_test import ArchesTestCase
from django.urls import reverse
from django.core import management
from django.test.client import RequestFactory, Client
from arches.app.views.api import APIBase
from arches.app.models import models
from arches.app.models.graph import Graph
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from django.contrib.auth.models import User, Group, AnonymousUser
from guardian.shortcuts import assign_perm

# these tests can be run from the command line via
# python manage.py test tests/views/api_tests.py --pattern="*.py" --settings="tests.test_settings"


class APITests(ArchesTestCase):

    def setUp(self):
            self.test_resource_existing_record = {
            "displaydescription": " We're knights of the Round Table, we dance whene'er we're able.",
            "displayname": " Knights of Camelot",
            "graph_id": "330802c5-95bd-11e8-b7ac-acde48001122",
            "legacyid": "I have to push the pram a lot.",
            "map_popup": "We're knights of the Round Table, we dance whene'er we're able.",
            "resourceinstanceid": "075957c4-d97f-4986-8d27-c32b6dec8e62",
            "tiles": [
                {
                    "data": {
                        "46f4da0c-95bd-11e8-8f87-acde48001122": None,
                        "4f553551-95bd-11e8-8b48-acde48001122": "Knights of Camelot",
                        "65f87f4c-95bd-11e8-b7a6-acde48001122": "We're knights of the Round Table, we dance whene'er we're able.",
                    },
                    "nodegroup_id": "46f4da0c-95bd-11e8-8f87-acde48001122",
                    "parenttile_id": None,
                    "provisionaledits": None,
                    "resourceinstance_id": "075957c4-d97f-4986-8d27-c32b6dec8e62",
                    "sortorder": 0,
                    "tileid": "39cd6433-370c-471d-85a7-64de182fce6b",
                },
                {
                    "data": {
                        "be993840-95c3-11e8-b08a-acde48001122": None,
                        "dfb05368-95c3-11e8-809b-acde48001122": [
                            {
                                "file_id": "64d698ae-9c5f-433c-967a-f037261dc369",
                                "name": "ffffff",
                                "status": "",
                                "type": "",
                                "url": "/files/uploadedfiles/ffffff",
                            }
                        ],
                    },
                    "nodegroup_id": "be993840-95c3-11e8-b08a-acde48001122",
                    "parenttile_id": None,
                    "provisionaledits": None,
                    "resourceinstance_id": "075957c4-d97f-4986-8d27-c32b6dec8e62",
                    "sortorder": 0,
                    "tileid": "a559fff5-2113-49c6-a34e-2e8b92a08a90",
                },
                {
                    "data": {"e7364d1e-95c4-11e8-9e7c-acde48001122": None, "f08a3057-95c4-11e8-9761-acde48001122": 63.0},
                    "nodegroup_id": "e7364d1e-95c4-11e8-9e7c-acde48001122",
                    "parenttile_id": None,
                    "provisionaledits": None,
                    "resourceinstance_id": "075957c4-d97f-4986-8d27-c32b6dec8e62",
                    "sortorder": 0,
                    "tileid": "ecd96a8e-9f95-490a-8093-bbe157089656",
                },
                {
                    "data": {
                        "c0197fe6-95c5-11e8-8394-acde48001122": None,
                        "c7d493b3-95c5-11e8-b554-acde48001122": "true",
                        "df6311f3-95ed-11e8-a289-acde48001122": "true",
                    },
                    "nodegroup_id": "c0197fe6-95c5-11e8-8394-acde48001122",
                    "parenttile_id": None,
                    "provisionaledits": None,
                    "resourceinstance_id": "075957c4-d97f-4986-8d27-c32b6dec8e62",
                    "sortorder": 0,
                    "tileid": "1c115557-8a9d-47a7-994f-11624e2efc88",
                },
                {
                    "data": {
                        "2e3b04c0-95ed-11e8-b68c-acde48001122": None,
                        "38870840-95ed-11e8-b2a9-acde48001122": {
                            "features": [
                                {
                                    "geometry": {"coordinates": [-122.3368509095547, 37.10722439718975], "type": "Point"},
                                    "id": "c2923742-99bc-48dc-acd0-1236dc728582",
                                    "properties": {},
                                    "type": "Feature",
                                }
                            ],
                            "type": "FeatureCollection",
                        },
                    },
                    "nodegroup_id": "2e3b04c0-95ed-11e8-b68c-acde48001122",
                    "parenttile_id": None,
                    "provisionaledits": None,
                    "resourceinstance_id": "075957c4-d97f-4986-8d27-c32b6dec8e62",
                    "sortorder": 0,
                    "tileid": "7e981761-0605-42ec-82bb-db42113daa60",
                },
                {
                    "data": {
                        "318c9e2b-a017-11e8-a36c-0200ec49ad01": [
                            "8c08196e-90bb-4359-b4ca-733861409de6",
                            "118b4e63-4466-494c-94ac-4cb98886c372",
                        ],
                        "ba84cc78-95bd-11e8-b8f5-acde48001122": None,
                        "c386a030-95bd-11e8-bff6-acde48001122": "118b4e63-4466-494c-94ac-4cb98886c372",
                        "d3089738-95bd-11e8-aa23-acde48001122": "118b4e63-4466-494c-94ac-4cb98886c372",
                        "feee2b85-a017-11e8-8460-0200ec49ad01": [
                            "8c08196e-90bb-4359-b4ca-733861409de6",
                            "118b4e63-4466-494c-94ac-4cb98886c372",
                        ],
                    },
                    "nodegroup_id": "ba84cc78-95bd-11e8-b8f5-acde48001122",
                    "parenttile_id": None,
                    "provisionaledits": None,
                    "resourceinstance_id": "075957c4-d97f-4986-8d27-c32b6dec8e62",
                    "sortorder": 0,
                    "tileid": "dc342949-661e-4ed0-9234-97f18d9ae483",
                },
                {
                    "data": {
                        "340c4817-95c3-11e8-b9e1-acde48001122": None,
                        "3dcfea07-95c3-11e8-b4da-acde48001122": "3d4ad50d-d855-4e40-8e78-911922977ba8",
                        "4ff64c70-95c3-11e8-8c25-acde48001122": "ad1aa626-7380-4b1c-8133-11fa1fed05eb",
                        "57b9e1a1-a017-11e8-b8c2-0200ec49ad01": [
                            "9561c1ae-0ae8-478c-b465-33ae8f6f27ca",
                            "ccfc0ac3-17b1-4672-8183-e02d419fe133",
                        ],
                    },
                    "nodegroup_id": "340c4817-95c3-11e8-b9e1-acde48001122",
                    "parenttile_id": None,
                    "provisionaledits": None,
                    "resourceinstance_id": "075957c4-d97f-4986-8d27-c32b6dec8e62",
                    "sortorder": 0,
                    "tileid": "57ec7d61-e71c-481b-bcad-6ec9a0631dec",
                },
                {
                    "data": {
                        "10fef7c0-a017-11e8-99b0-0200ec49ad01": "2010-10",
                        "5ebe6bc2-95c4-11e8-9dac-acde48001122": "1926-01-06",
                        "d3e98b97-95c3-11e8-a9b2-acde48001122": None,
                    },
                    "nodegroup_id": "d3e98b97-95c3-11e8-a9b2-acde48001122",
                    "parenttile_id": None,
                    "provisionaledits": None,
                    "resourceinstance_id": "075957c4-d97f-4986-8d27-c32b6dec8e62",
                    "sortorder": 0,
                    "tileid": "0c63341c-0663-4c39-b554-df69f0bd7904",
                },
            ],
        }
            self.test_resource_simple = {"resourceinstanceid": "1dbfe5fe-b6fe-484b-a58c-4d080d427e80", 
                                                  "graph_id": "330802c5-95bd-11e8-b7ac-acde48001122", 
                                                  "legacyid": "", "tiles": []}

    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        geojson_nodeid = "3ebc6785-fa61-11e6-8c85-14109fd34195"
        cls.loadOntology()
        with open(os.path.join("tests/fixtures/resource_graphs/unique_graph_shape.json"), "rU") as f:
            json = JSONDeserializer().deserialize(f)
            cls.unique_graph = Graph(json["graph"][0])
            cls.unique_graph.save()

        with open(os.path.join("tests/fixtures/resource_graphs/ambiguous_graph_shape.json"), "rU") as f:
            json = JSONDeserializer().deserialize(f)
            cls.ambiguous_graph = Graph(json["graph"][0])
            cls.ambiguous_graph.save()

        with open(os.path.join("tests/fixtures/resource_graphs/phase_type_assignment.json"), "rU") as f:
            json = JSONDeserializer().deserialize(f)
            cls.phase_type_assignment_graph = Graph(json["graph"][0])
            cls.phase_type_assignment_graph.save()

        # Load the test package to provide resources graph.
        test_pkg_path = os.path.join(test_settings.TEST_ROOT, "fixtures", "testing_prj", "testing_prj", "pkg")
        management.call_command("packages", operation="load_package", source=test_pkg_path, yes=True)

        
        breakpoint()

        cls.set_up_users_and_groups()


    @classmethod
    def set_up_users_and_groups(cls):
        cls.users = {}
        cls.users["System Administrator"] = User.objects.create_user(username="SystemAdministratorUser", password="SystemAdministratorUser", is_superuser=True, is_staff=True)
        cls.users["Application Administrator"] = User.objects.create_user(username="ApplicationAdministratorUser", password="ApplicationAdministratorUser", is_superuser=True, is_staff=True)
        cls.users["Graph Editor"] = User.objects.create_user(username="GraphEditorUser", password="GraphEditorUser", is_superuser=False, is_staff=False)
        cls.users["Resource Editor"] = User.objects.create_user(username="ResourceEditorUser", password="ResourceEditorUser", is_superuser=False, is_staff=False)
        cls.users["RDM Administrator"] = User.objects.create_user(username="RDMAdministratorUser", password="RDMAdministratorUser", is_superuser=False, is_staff=False)
        cls.users["Mobile Project Administrator"] = User.objects.create_user(username="MobileProjectAdministratorUser", password="MobileProjectAdministratorUser", is_superuser=False, is_staff=False)
        cls.users["Crowdsource Editor"] = User.objects.create_user(username="CrowdsourceEditorUser", password="CrowdsourceEditorUser", is_superuser=False, is_staff=False)
        cls.users["Guest"] = User.objects.create_user(username="GuestUser", password="GuestUser", is_superuser=False, is_staff=False)
        cls.users["Resource Reviewer"] = User.objects.create_user(username="ResourceReviewerUser", password="ResourceReviewerUser", is_superuser=False, is_staff=False)

        # DELIBERATELYREMMED OUT - Default User groups which do not seem to exist.
        # cls.users["All Workflows"] = User.objects.create_user(username="AllWorkflowsUser", password="AllWorkflowsUser", is_superuser=False, is_staff=False)
        # cls.users["External Users"] = User.objects.create_user(username="ExternalUsersUser", password="ExternalUsersUser", is_superuser=False, is_staff=False)
        # cls.users["No Ordnance Survey Mapping"] = User.objects.create_user(username="NoOrdnanceSurveyMappingUser", password="NoOrdnanceSurveyMappingUser", is_superuser=False, is_staff=False)
        # cls.users["Access to Consultations and Application Areas"] = User.objects.create_user(username="AccessToConsultationsAndApplicationAreasUser", password="AccessToConsultationsAndApplicationAreasUser", is_superuser=False, is_staff=False)
        # cls.users["Search Exporters"] = User.objects.create_user(username="SearchExportersUser", password="SearchExportersUser", is_superuser=False, is_staff=False)

        for key, user in cls.users.items():
            group, created = Group.objects.get_or_create(name=key)
            if created:
                raise AssertionError(f"Group '{key}' did not already exist.")
            user.groups.add(group)



    # From Database auth_group_permissions, auth_permission and auth_group tables, 
    # select ag.*, ap.* from public.auth_group ag
    # left join public.auth_group_permissions agp on agp.group_id = ag.id
    # left join public.auth_permission ap on agp.permission_id = ap.id
    # #
    expected_status = {
        "System Administrator":     {"post": 201, "get": 200, "put": 201, "delete": 200},
        "Graph Editor":     {"post": 201, "get": 200, "put": 201, "delete": 200},
        "Resource Editor": {"post": 201, "get": 200, "put": 201, "delete": 200},
        "RDM Administrator": {"post": 403, "get": 403, "put": 403, "delete": 403},
        "Application Administrator": {"post": 201, "get": 200, "put": 201, "delete": 200},
        "Mobile Project Administrator": {"post": 403, "get": 403, "put": 403, "delete": 403},
        "Crowdsource Editor": {"post": 403, "get": 403, "put": 403, "delete": 403},
        "Guest": {"post": 403, "get": 200, "put": 403, "delete": 403},
        "AnonymousUser": {"post": 403, "get": 200, "put": 403, "delete": 403},
        "Resource Reviewer":  {"post": 201, "get": 200, "put": 201, "delete": 200},
        "All Workflows": {"post": 403, "get": 403, "put": 201, "delete": 403},
        "External Users": {"post": 403, "get": 403, "put": 403, "delete": 403},
        "No Ordnance Survey Mapping": {"post": 403, "get": 403, "put": 403, "delete": 403},
        "Access to Consultations and Application Areas": {"post": 403, "get": 403, "put": 403, "delete": 403},
        "Search Exporters": {"post": 403, "get": 403, "put": 403, "delete": 403},
    }

    
    def _call_api_method(self, method, url, payload, content_type):
        if method == "post":
            return self.client.post(url, payload, content_type)
        elif method == "get":
            return self.client.get(url)
        elif method == "put":
            return self.client.put(url, payload, content_type)
        elif method == "delete":
            return self.client.delete(url)



    def test_00_single_User_verbs_resource(self):
        """
        Test POST, GET, PUT and DELETE of a single resource by a single user for DEBUGGING.        
        """

        for username, user in self.users.items():
                            
            breakpoint()

            print(f"Testing API methods for user: {username}")

            payload = JSONSerializer().serialize(self.test_resource_simple)
            content_type = "application/json"
            self.client.login(username=user.username, password=user.username)

            # Act : PUT resource to database with new resourceinstanceid to create new resource
            resp_put_create = self.client.put(
                reverse("resources", kwargs={"resourceid": self.test_resource_simple["resourceinstanceid"]}) + "?format=arches-json",
                payload,
                content_type,
            )
            
            print(f"PUT response status code: {resp_put_create.status_code}")         
            # Amend legacyid on payload to avoid key violations.
            self.test_resource_simple["legacyid"] = self.test_resource_simple["legacyid"] + "Spam, "
            payload = JSONSerializer().serialize(self.test_resource_simple)


            resp_post_create = self.client.post(
                reverse("resources", kwargs={"resourceid": self.test_resource_simple["resourceinstanceid"]}) + "?format=arches-json",
                payload,
                content_type,
            )

            print(f"POST response status code: {resp_post_create.status_code}") 
            # Amend legacyid on payload to avoid key violations.
            self.test_resource_simple["legacyid"] = self.test_resource_simple["legacyid"] + "Spam, "
            payload = JSONSerializer().serialize(self.test_resource_simple)

            # We need an existing record to test get and delete against.
            if resp_post_create.status_code == 201:
                resp_post_create_resource = JSONDeserializer().deserialize(resp_post_create.content)  # get the resourceinstance returned.
                my_resource_resourceinstanceid = resp_post_create_resource[0]["resourceinstanceid"]
            else:
                self.client.login(username="SystemAdministratorUser", password="SystemAdministratorUser")
                # Amend legacyid on payload to avoid key violations.
                self.test_resource_simple["legacyid"] = self.test_resource_simple["legacyid"] + "Spam, "
                payload = JSONSerializer().serialize(self.test_resource_simple)

                resp_existing = self.client.put(
                    reverse("resources", kwargs={"resourceid": self.test_resource_simple["resourceinstanceid"]}) + "?format=arches-json",
                    payload,
                    content_type,
                    )            
                if resp_existing.status_code != 201:
                    self.fail(f"Failed to create test pre-existing-resource: {resp_existing.status_code}")
                else:
                    resp_existing_resource = JSONDeserializer().deserialize(resp_existing.content)  # get the resourceinstance returned.
                    my_resource_resourceinstanceid = resp_existing_resource[0]["resourceinstanceid"]
                self.client.login(username=user.username, password=user.username)

            # GET
            resp_get = self.client.get(reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json")
            print(f"GET response status code: {resp_get.status_code}")

            # PUT with existing resourceinstanceid should update resource, not create new one.
            # Amend legacyid on payload to avoid key violations.
            self.test_resource_simple["legacyid"] = self.test_resource_simple["legacyid"] + "Spam, "
            payload = JSONSerializer().serialize(self.test_resource_simple)

            # PUT -  (The resourceinstanceid in the URI and payload must match.)
            resp_put_update = self.client.put(
                reverse("resources", kwargs={"resourceid": self.test_resource_simple["resourceinstanceid"]}) + "?format=arches-json",
                payload,
                content_type,
            )
            print(f"PUT with existing resourceinstanceid response status code: {resp_put_update.status_code}")

            # DELETE
            resp_delete = self.client.delete(reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json")
            print(f"DELETE response status code: {resp_delete.status_code}")

        # Assert
        self.assertEqual(True, True, "Nonsense assertion, but completed debug output!") 


##############################################################################################
#
#  Main tests under dev.

    # def test_01_api_permissions_group(self):
    #     api_methods = ["post", "get", "put", "delete"]
    #     content_type = "application/json"

    #     payload_existing_record = JSONSerializer().serialize(self.test_resource_existing_record)
    #     url_existing_record = reverse("resources", kwargs={"resourceid": self.test_resource_existing_record["resourceinstanceid"]}) + "?format=arches-json"

    #     payload_user_record = JSONSerializer().serialize(self.test_resource_simple)
    #     url_user_record = reverse("resources", kwargs={"resourceid": self.test_resource_simple["resourceinstanceid"]}) + "?format=arches-json"

    #     # Add AnonymousUser for testing
    #     self.users["AnonymousUser"] = AnonymousUser()

    #     for username, user in self.users.items():

    #         # Create a resource as admin to test permissions for other users on an existing resource, and to provide a resourceinstanceid for testing PUT with existing resourceinstanceid and DELETE.
    #         self.client.login(username="SystemAdministratorUser", password="SystemAdministratorUser")
    #         resp_existing = self.client.put(url_existing_record, payload_existing_record, content_type)            
    #         if resp_existing.status_code != 201:
    #             self.fail(f"Failed to create test pre-existing-resource: {resp_existing.status_code}")

    #         for method in api_methods:
    #             with self.subTest(user=username, method=method):                    
    #                 # Login as the user for this subtest, or logout if AnonymousUser.
    #                 if username != "AnonymousUser":
    #                     self.client.login(username=username, password=username)
    #                 else:
    #                     self.client.logout()

    #                 if method == "post":
    #                     # POST - Used to create a new resource. (The resourceinstanceid in the payload is usually ignored or overwritten by the server.)
    #                     response = self.client.post(url_user_record, payload_user_record, content_type)   
    #                     if response.status_code == 201:
    #                         # If POST succeeded, amend legacyid on payload_user_record to avoid key violations.
    #                         self.test_resource_simple["legacyid"] = self.test_resource_simple["legacyid"] + "Spam, "
    #                         payload_user_record = JSONSerializer().serialize(self.test_resource_simple)                           
    #                 elif method == "get":
    #                     response = self.client.get(url_existing_record)
    #                 elif method =="put":

    #                     # PUT -  Used to update an existing resource, or create it if it does not exist (upsert). (The resourceinstanceid in the URI and payload must match.)
    #                     response = self.client.put(url_existing_record, payload_existing_record, content_type) 
    #                 elif method == "delete":
    #                     response = self.client.delete(url_existing_record)
    #                 self.assertEqual(response.status_code, self.expected_status[username][method], f"{username} {method} failed")


    # def test_02_api_permissions_group_vs_user(self):
    #     """
    #     Test API responses for users with and without sufficient privileges cf. group permissions, and test that object permissions for 
    #     a resourceinstance override group permissions for that resourceinstance, for both privileged and unprivileged users.
    #     """
    #     breakpoint()

    #     # Create privileged/deprivileged users and privileged/deprivileged group users
    #     privileged_user = User.objects.create_user(username="privileged", password="privileged")
    #     deprivileged_user = User.objects.create_user(username="deprivileged", password="deprivileged")
    #     privileged_group_deprivileged_user = User.objects.create_user(username="privileged_group", password="privileged_group")
    #     deprivileged_group_privileged_user = User.objects.create_user(username="deprivileged_group", password="deprivileged_group")
        
    #     # Add privileged_group_deprivileged_user to privilegedGroup group
    #     group_privileged = Group.objects.create(name="privilegedGroup")
    #     privileged_group_deprivileged_user.groups.add(group_privileged)

    #     # Add deprivileged_group_privileged_user to deprivilegedGroup group (add deny permissions when test *resourceinstance* created below)
    #     group_deprivileged = Group.objects.create(name="deprivilegedGroup")
    #     deprivileged_group_privileged_user.groups.add(group_deprivileged)

    #     # Set up test resource data under admin user      
    #     payload = JSONSerializer().serialize(self.test_resource_simple)
    #     content_type = "application/json"
    #     self.client.login(username="admin", password="admin")

    #     resp_post = self.client.post(
    #         reverse("resources", kwargs={"resourceid": "075957c4-d97f-4986-8d27-c32b6dec8e62"}) + "?format=arches-json",
    #         payload,
    #         content_type,
    #     )
    #     self.assertEqual(resp_post.status_code, 201, "POST should create resource (201 Created)")  # resource created.
    #     # Retrieve the resource instance
    #     resource_instance_data = JSONDeserializer().deserialize(resp_post.content)
    #     my_resource_resourceinstanceid = resource_instance_data[0]["resourceinstanceid"]
    #     resource_instance = Resource.objects.get(resourceinstanceid=my_resource_resourceinstanceid)

    #     # Add privileged user to view_resourceinstance object permission for the test *resourceinstance*
    #     assign_perm("view_resourceinstance", privileged_user, resource_instance)
    #     # Add privileged group to view_resourceinstance object permission for the test *resourceinstance*
    #     assign_perm("view_resourceinstance", group_privileged, resource_instance)
    #     # Add deprivileged user to no_access_to_resourceinstance object permission for the test *resourceinstance*
    #     assign_perm("no_access_to_resourceinstance", deprivileged_user, resource_instance)
    #     # Add deprivileged group to no_access_to_resourceinstance object permission for the test *resourceinstance*
    #     assign_perm("no_access_to_resourceinstance", group_deprivileged, resource_instance)


    #     self.client.login(username="privileged", password="privileged")
    #     resp_priv = self.client.get(reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json")
    #     self.assertEqual(resp_priv.status_code, 200, "privileged user should GET 200 OK")

    #     self.client.login(username="deprivileged", password="deprivileged")
    #     resp_priv = self.client.get(reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json")
    #     self.assertEqual(resp_priv.status_code, 403, "deprivileged user should GET 403 Forbidden")

    #     self.client.login(username="privileged_group", password="privileged_group")
    #     resp_priv = self.client.get(reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json")
    #     self.assertEqual(resp_priv.status_code, 200, "privileged group user should GET 200 OK")

    #     self.client.login(username="deprivileged_group", password="deprivileged_group")
    #     resp_depriv = self.client.get(reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json")
    #     self.assertEqual(resp_depriv.status_code, 403, "Deprivileged group user should get 403 Forbidden")

    #     # Test Conflicting permissions  - Individual user permissions should override group permissions      

    #     # deprivileged_group_deprivileged_user should be forbidden to GET resource.
    #     self.client.login(username="deprivileged_group", password="deprivileged_group")
    #     resp_priv = self.client.get(reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json")
    #     self.assertEqual(resp_priv.status_code, 403, "deprivileged_group_privileged_user user should GET 403 Forbidden due to individual user deny permission overriding group allow permission")

    #     # privileged_group_deprivileged_user should be able to GET resource
    #     self.client.login(username="privileged_group", password="privileged_group")
    #     resp_priv = self.client.get(reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json")
    #     self.assertEqual(resp_priv.status_code, 200, "privileged_group_deprivileged_user user should GET 200 OK")


    #     # Clean up
    #     privileged_user.delete()
    #     deprivileged_user.delete()
    #     privileged_group_deprivileged_user.delete()
    #     deprivileged_group_privileged_user.delete()

 ##############################################################################################
 # 
 #   Scratchpad for developing tests for APIBase view, and POST and PUT of resources endpoint with arches-json format data.
 # 
 ###############################################################################################

    # def test_01_api_base_view(self):
    #     """
    #     Test that our custom header parameters get pushed on to the GET QueryDict

    #     """

    #     factory = RequestFactory(HTTP_X_ARCHES_VER="2.1")
    #     view = APIBase.as_view()

    #     # request = factory.get(reverse("mobileprojects", kwargs={}), {"ver": "2.0"})
    #     # request.user = None
    #     # response = view(request)
    #     # self.assertEqual(request.GET.get("ver"), "2.0")

    #     # request = factory.get(reverse("mobileprojects"), kwargs={})
    #     # request.user = None
    #     # response = view(request)
    #     # self.assertEqual(request.GET.get("ver"), "2.1")

    # def test_02_api_resources_archesjson(self):
    #     """
    #     Test that resources POST and PUT accept arches-json format data.
    #     """
    #     # ==Arrange=========================================================================================
       
    #     payload = JSONSerializer().serialize(self.test_resource_simple)
    #     content_type = "application/json"
    #     self.client.login(username="admin", password="admin")

    #     # ==POST============================================================================================

    #     # ==Act : POST resource to database (N.B. resourceid supplied will be overwritten by arches)========
    #     resp_post = self.client.post(
    #         reverse("resources", kwargs={"resourceid": "075957c4-d97f-4986-8d27-c32b6dec8e62"}) + "?format=arches-json",
    #         payload,
    #         content_type,
    #     )
    #     # ==Assert==========================================================================================
    #     self.assertEqual(resp_post.status_code, 201, "POST should create resource (201 Created)")  # resource created.
    #     my_resource = JSONDeserializer().deserialize(resp_post.content)  # get the resourceinstance returned.
    #     self.assertEqual(my_resource[0]["legacyid"], "I have to push the pram a lot.", "POST returned resource with correct legacyid")  # Success, we were returned the right one.
    #     my_resource_resourceinstanceid = my_resource[0]["resourceinstanceid"]  # get resourceinstanceid.
    #     # ==================================================================================================

    #     # ==Act : GET confirmation that resource does now exist in database=================================
    #     resp_get_confirm = self.client.get(
    #         reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json"
    #     )
    #     # ==Assert==========================================================================================
    #     self.assertEqual(resp_get_confirm.status_code, 200, "GET after POST should succeed (200 OK)")  # Success, we got one.
    #     data_get_confirm = JSONDeserializer().deserialize(resp_get_confirm.content)
    #     self.assertEqual(
    #         data_get_confirm["tiles"][0]["data"]["65f87f4c-95bd-11e8-b7a6-acde48001122"],
    #         "We're knights of the Round Table, we dance whene'er we're able.", "GET after POST returned correct tile data"
    #     )  # Success, we got the right one.
    #     # ==================================================================================================

    #     # ==Arrange=========================================================================================

    #     # modify test_resource_simple
    #     self.test_resource_simple["tiles"][0]["data"][
    #         "65f87f4c-95bd-11e8-b7a6-acde48001122"
    #     ] = "We do routines and chorus scenes with footwork impec-cable.."
    #     self.test_resource_simple["legacyid"] = "we eat ham and jam and Spam a lot."  # legacyid has a unique index constraint.
    #     payload_modified = JSONSerializer().serialize(self.test_resource_simple)

    #     # ==PUT=============================================================================================

    #     # ==Act : GET confirmation that resource does not exist in database=================================
    #     with self.assertRaises(models.ResourceInstance.DoesNotExist) as context:
    #         resp_get = self.client.get(
    #             reverse("resources", kwargs={"resourceid": "075957c4-d97f-4986-8d27-c32b6dec8e62"}) + "?format=arches-json"
    #         )
    #     # ==Assert==========================================================================================
    #     self.assertTrue("Resource matching query does not exist." in str(context.exception), "GET for deleted resource should raise DoesNotExist")  # Check exception message.
    #     # ==================================================================================================

    #     # ==Act : PUT resource changes to database for new resourceinstanceid to create new resource=========
    #     resp_put_create = self.client.put(
    #         reverse("resources", kwargs={"resourceid": "075957c4-d97f-4986-8d27-c32b6dec8e62"}) + "?format=arches-json",
    #         payload_modified,
    #         content_type,
    #     )

    #     # ==Assert==========================================================================================
    #     self.assertEqual(resp_put_create.status_code, 201, "PUT with new resourceinstanceid should create resource (201 Created)")  # resource created.
    #     resp_put_create_resource = JSONDeserializer().deserialize(resp_put_create.content)  # get the resourceinstance returned.
    #     self.assertEqual(
    #         resp_put_create_resource[0]["legacyid"], "we eat ham and jam and Spam a lot.", "PUT with new resourceinstanceid returned correct legacyid"
    #     )  # Success, we returned the right one.
    #     # ==================================================================================================

    #     # ==Act : GET confirmation that resource does now exist in database=================================
    #     resp_put_get_confirm = self.client.get(
    #         reverse("resources", kwargs={"resourceid": "075957c4-d97f-4986-8d27-c32b6dec8e62"}) + "?format=arches-json"
    #     )
    #     # ==Assert==========================================================================================
    #     self.assertEqual(resp_put_get_confirm.status_code, 200, "GET after PUT (new resource) should succeed (200 OK)")  # Success, we got one.
    #     data_put_get_confirm = JSONDeserializer().deserialize(resp_put_get_confirm.content)

    #     tile = next(x for x in data_put_get_confirm["tiles"] if x["tileid"] == "39cd6433-370c-471d-85a7-64de182fce6b")
    #     self.assertEqual(
    #         tile["data"]["65f87f4c-95bd-11e8-b7a6-acde48001122"],
    #         "We do routines and chorus scenes with footwork impec-cable..", "GET after PUT (new resource) returned correct tile data"
    #     )  # Success, we got the right one.
    #     # ==================================================================================================

    #     # ==Act : PUT resource changes to database, with invalid URI========================================
    #     resp_put_uri_diff = self.client.put(
    #         reverse("resources", kwargs={"resourceid": "001fe587-ad3d-4d0d-a3c9-814028766434"}) + "?format=arches-json",
    #         payload_modified,
    #         content_type,
    #     )
    #     # ==Assert==========================================================================================
    #     self.assertEqual(resp_put_uri_diff.status_code, 400, "PUT with mismatched resourceinstanceid should fail (400 Bad Request)")  # Bad Request.
    #     # ==================================================================================================

    #     # ==Arrange=========================================================================================

    #     # modify resourceinstanceid on modified test_resource_simple to that of initial POST resource.
    #     self.test_resource_simple["resourceinstanceid"] = my_resource_resourceinstanceid
    #     self.test_resource_simple["legacyid"] = "we sing from the diaphragm a lot."  # legacyid has a unique index constraint.
    #     payload_modified = JSONSerializer().serialize(self.test_resource_simple)

    #     # ==Act : PUT resource changes to initial POST database resource to overwrite=======================
    #     resp_put = self.client.put(
    #         reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json",
    #         payload_modified,
    #         content_type,
    #     )

    #     # ==Assert==========================================================================================
    #     self.assertEqual(resp_put.status_code, 201, "PUT to existing resourceinstanceid should update resource (201 Created)")  # resource created.
    #     data_resp_put_confirm_mod = JSONDeserializer().deserialize(resp_put.content)
    #     self.assertEqual(
    #         data_resp_put_confirm_mod[0]["legacyid"], "we sing from the diaphragm a lot.", "PUT to existing resourceinstanceid returned correct legacyid"
    #     )  # Success, we returned the right one.
    #     # ==================================================================================================

    #     # ==Act : GET confirmation that resource is now changed in database=================================
    #     resp_get_confirm_mod = self.client.get(
    #         reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json"
    #     )
    #     # ==Assert==========================================================================================
    #     self.assertEqual(resp_get_confirm_mod.status_code, 200, "GET after PUT (update) should succeed (200 OK)")  # Success, we got one.
    #     data_get_confirm_mod = JSONDeserializer().deserialize(resp_get_confirm_mod.content)

    #     tile = next(x for x in data_put_get_confirm["tiles"] if x["tileid"] == "39cd6433-370c-471d-85a7-64de182fce6b")
    #     self.assertEqual(
    #         tile["data"]["65f87f4c-95bd-11e8-b7a6-acde48001122"],
    #         "We do routines and chorus scenes with footwork impec-cable..", "GET after PUT (update) returned correct tile data"
    #     )
    #     # ==================================================================================================

    #     # ==Act : DELETE resource from database=============================================================
    #     resp_delete = self.client.delete(reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}))
    #     # ==Assert==========================================================================================
    #     self.assertEqual(resp_delete.status_code, 200, "DELETE should succeed (200 OK)")  # Success, we got rid of one.
    #     # ==================================================================================================

    #     # ==Act : GET confirmation that resource does not exist in database=================================
    #     with self.assertRaises(models.ResourceInstance.DoesNotExist) as context_del:
    #         resp_get_deleted = self.client.get(
    #             reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid}) + "?format=arches-json"
    #         )
    #     # ==Assert==========================================================================================
    #     self.assertTrue("Resource matching query does not exist." in str(context_del.exception), "GET after DELETE should raise DoesNotExist")  # Check exception message.
    #     # ==================================================================================================

    # # def test_04_resources_api_methods_permissions(self):
    #     """
    #     Test all Resources API methods (GET, POST, PUT, DELETE) for privileged and unprivileged users.
    #     """
    #     #breakpoint()
    #     privileged_user = User.objects.create_user(username="privileged", password="privileged")
    #     deprivileged_user = User.objects.create_user(username="deprivileged", password="deprivileged")
    #     deprivileged_group_user = User.objects.create_user(username="deprivileged_group", password="deprivileged_group")
    #     resource_editor_group, _ = Group.objects.get_or_create(name="Resource Editor")
    #     privileged_user.groups.add(resource_editor_group)
        
    #     # Add privileged user to Resource Editor group
    #     resource_editor_group, _ = Group.objects.get_or_create(name="Resource Editor")
    #     privileged_user.groups.add(resource_editor_group)

    #     # Add deprivileged group user to a group (add deny permissions when test *resourceinstance* created below)
    #     group_unprivileged = Group.objects.create(name="UnprivilegedGroup")
    #     deprivileged_group_user.groups.add(group_unprivileged)
    #     deprivileged_group_user.save()


    #     # Set up test resource data
    #     # ==Arrange=========================================================================================
       
    #     payload = JSONSerializer().serialize(self.test_resource_simple)
    #     content_type = "application/json"
    #     self.client.login(username="admin", password="admin")

    #     # ==POST============================================================================================

    #     # ==Act : POST resource to database (N.B. resourceid supplied will be overwritten by arches)========
    #     resp_post = self.client.post(
    #         reverse("resources", kwargs={"resourceid": "075957c4-d97f-4986-8d27-c32b6dec8e62"}) + "?format=arches-json",
    #         payload,
    #         content_type,
    #     )
    #     # ==Assert==========================================================================================
    #     self.assertEqual(resp_post.status_code, 201, "POST should create resource (201 Created)")  # resource created.
    #     my_resource = JSONDeserializer().deserialize(resp_post.content)  # get the resourceinstance returned.
    #     self.assertEqual(my_resource[0]["legacyid"], "I have to push the pram a lot.", "POST returned resource with correct legacyid")  # Success, we were returned the right one.
    #     my_resource_resourceinstanceid = my_resource[0]["resourceinstanceid"]  # get resourceinstanceid.
    #     # ==================================================================================================

    #     url = reverse("resources", kwargs={"resourceid": my_resource_resourceinstanceid})

    #     # Admin user tests
        
    #     # # POST
    #     # # Used to create a new resource.
    #     # # The resourceinstanceid in the payload is usually ignored or overwritten by the server.
    #     self.assertNotEqual(resp_post.status_code, 403, "Admin user POST should not get 403 Forbidden")
    #     self.assertEqual(resp_post.status_code, 201, "Admin user POST should get 201 Created")
    #     # GET
    #     resp_get = self.client.get(url + "?format=arches-json")
    #     self.assertNotEqual(resp_get.status_code, 403, "Admin user GET should not get 403 Forbidden")
    #     self.assertEqual(resp_get.status_code, 200, "Admin user GET should get 200 OK")
    #     # DELETE
    #     resp_delete = self.client.delete(url)
    #     self.assertNotEqual(resp_delete.status_code, 403, "Admin user DELETE should not get 403 Forbidden")
    #     self.assertEqual(resp_delete.status_code, 200, "Admin user DELETE should get 200 OK")
    #     # # PUT
    #     # # Used to update an existing resource, or create it if it does not exist (upsert). 
    #     # # The resourceinstanceid in the URI and payload must match.

    #     payload_put = JSONSerializer().serialize({"resourceinstanceid": my_resource_resourceinstanceid, 
    #                                               "graph_id": "330802c5-95bd-11e8-b7ac-acde48001122", 
    #                                               "legacyid": "", "tiles": []})

    #     resp_put = self.client.put(url + "?format=arches-json", payload_put, content_type)
    #     self.assertNotEqual(resp_put.status_code, 403, "Admin user PUT should not get 403 Forbidden")
    #     self.assertEqual(resp_put.status_code, 201, "Admin user PUT should get 201 Created")

    #     # Privileged user tests
    #     self.client.login(username="privileged", password="privileged")
    #     # POST
    #     resp_post = self.client.post(url + "?format=arches-json", payload, content_type)
    #     self.assertNotEqual(resp_post.status_code, 403, "Privileged user POST should not get 403 Forbidden")
    #     self.assertEqual(resp_post.status_code, 201, "Privileged user POST should get 201 Created")
    #     # GET
    #     resp_get = self.client.get(url + "?format=arches-json")
    #     self.assertNotEqual(resp_get.status_code, 403, "Privileged user GET should not get 403 Forbidden")
    #     self.assertEqual(resp_get.status_code, 200, "Privileged user GET should get 200 OK")
    #     # PUT
    #     resp_put = self.client.put(url + "?format=arches-json", payload_put, content_type)
    #     self.assertNotEqual(resp_put.status_code, 403, "Privileged user PUT should not get 403 Forbidden")
    #     self.assertEqual(resp_put.status_code, 201, "Privileged user PUT should get 201 Created")
    #     # DELETE
    #     resp_delete = self.client.delete(url)
    #     self.assertNotEqual(resp_delete.status_code, 403, "Privileged user DELETE should not get 403 Forbidden")
    #     self.assertEqual(resp_delete.status_code, 200, "Privileged user DELETE should get 200 OK")

    #     # Deprivileged user tests
    #     self.client.login(username="deprivileged", password="deprivileged")
    #     # POST
    #     resp_post_depriv = self.client.post(url + "?format=arches-json", payload, content_type)
    #     self.assertEqual(resp_post_depriv.status_code, 403, "Deprivileged user POST should get 403 Forbidden")
    #     # GET
    #     resp_get_depriv = self.client.get(url + "?format=arches-json")
    #     self.assertEqual(resp_get_depriv.status_code, 403, "Deprivileged user GET should get 403 Forbidden")
    #     # PUT
    #     resp_put_depriv = self.client.put(url + "?format=arches-json", payload_put, content_type)
    #     self.assertEqual(resp_put_depriv.status_code, 403, "Deprivileged user PUT should get 403 Forbidden")
    #     # DELETE
    #     resp_delete_depriv = self.client.delete(url)
    #     self.assertEqual(resp_delete_depriv.status_code, 403, "Deprivileged user DELETE should get 403 Forbidden")

    #     # Clean up
    #     privileged_user.delete()
    #     deprivileged_user.delete()
    #     deprivileged_group_user.delete()
    #     resource_editor_group.delete()
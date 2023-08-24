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

from arches.management.commands import utils
import uuid
from arches.app.models import models
from arches.app.models.graph import Graph
from arches.app.models.resource import Resource
from django.core.management.base import BaseCommand, CommandError
import arches.app.utils.data_management.resources.remover as resource_remover
from arches.app.utils.index_database import index_resources_using_multiprocessing as index_resources_using_multiprocessing


class Command(BaseCommand):
    """
    Commands for managing Arches functions

    """

    def add_arguments(self, parser):
        parser.add_argument("operation", nargs="?")

        parser.add_argument(
            "-y", "--yes", action="store_true", dest="yes", help='used to force a yes answer to any user input "continue? y/n" prompt'
        )

        parser.add_argument(
            "-g",
            "--graph",
            action="store",
            dest="graph",
            help="A graphid of the Resource Model you would like to remove all instances from.",
        )


        parser.add_argument(
            "--dont_index",
            action="store_false",
            dest="dont_index"
        )

    def handle(self, *args, **options):
        if options["operation"] == "remove_resources":
            self.remove_resources(force=options["yes"], graphid=options["graph"])
        if options["operation"] == "obfuscate_node_values":
            self.obfuscate_node_values(index=options["dont_index"], force=options["yes"])
            

    def remove_resources(self, load_id="", graphid=None, force=False):
        """
        Runs the resource_remover command found in data_management.resources
        """
        # resource_remover.delete_resources(load_id)
        if not force:
            if graphid is None:
                if not utils.get_yn_input("all resources will be removed. continue?"):
                    return
            else:
                if not utils.get_yn_input(
                    "All resources associated with the '%s' Resource Model will be removed. continue?"
                    % Graph.objects.get(graphid=graphid).name
                ):
                    return

        if graphid is None:
            resource_remover.clear_resources()
        else:
            graph = Graph.objects.get(graphid=graphid)
            graph.delete_instances(verbose=True)

        return
    

    NODES_TO_CHANGE_TEMPLATE = [
        {
            "nodeid": "<nodeid of values to obfuscate>", # uuid
            "value_type": "<key name of random value to use>", # see the generate_random_data_dict function for options
            "one_per_resource": False , # if True, only one random value dict will be generated per resourceinstanceid. If False, a new random value dict will be generated for each node value to be obfuscated.
            "where_nodeid": "", # nodeid on the same tile to check before updating the target value (e.g. check the contact point is an email before updating the node using the email value)
            "where_op":"equals", # or "contains". The node value will only be updated if the where_nodeid value matches the where_value using the where_op operator
            "where_value": "" # the value to check against the where_nodeid value
         }

        """
         Update "nodeid" with a random value of "value_type" where the "where_nodeid" value is (as given by the where_op) equal to, or contains the value of, the where_value
        """
    ]

    NODES_TO_CHANGE = [
        #####person 
        ##{"nodeid": "6da2f03b-7e55-11ea-8fe5-f875a44e0e11", "value_type": "title_id", "one_per_resource": True}, #title
        ##{"nodeid": "2caeb5e7-7b44-11ea-a919-f875a44e0e11", "value_type": "first_name", "one_per_resource": True}, #Forenames
        ##{"nodeid": "96a3942a-7e53-11ea-8b5a-f875a44e0e11", "value_type": "last_name", "one_per_resource": True}, #Surname
        ##{"nodeid": "5f8ded26-7ef9-11ea-8e29-f875a44e0e11", "value_type": "full_name", "one_per_resource": True}, #Full name
        ##{"nodeid": "2547c133-9505-11ea-8e49-f875a44e0e11", "value_type": "email", "one_per_resource": True, "where_nodeid": "2547c132-9505-11ea-b22f-f875a44e0e11", , "where_op":"equals", "where_value": "0f466b8b-a347-439f-9b61-bee9811ccbf0"}, #contact point where type is EMAIL
        ##{"nodeid": "2547c133-9505-11ea-8e49-f875a44e0e11", "value_type": "full_address", "one_per_resource": True, "where_nodeid": "2547c132-9505-11ea-b22f-f875a44e0e11", "where_op":"equals", "where_value": "e6d433a2-7f77-4eb7-96f2-57ebe0ac251e"}, #contact point where type is MAIL
        ##{"nodeid": "2547c133-9505-11ea-8e49-f875a44e0e11", "value_type": "phone_number", "one_per_resource": True, "where_nodeid": "2547c132-9505-11ea-b22f-f875a44e0e11", "where_op":"equals", "where_value": "75e6cfad-7418-4ed3-841b-3c083d7df30b"}, #contact point where type is TELEPHONE
        ##{"nodeid": "2beefb56-4084-11eb-bcc5-f875a44e0e11", "value_type": "full_name", "one_per_resource": True}, #contact name correspondance
        #####bibliographic author, editor, contributor
        ##{"nodeid": "c06e676e-95ef-11ea-a32a-f875a44e0e11", "value_type": "author_name", "one_per_resource": False}, #bibliographic author
        ##{"nodeid": "c06e6768-95ef-11ea-bf92-f875a44e0e11", "value_type": "author_name", "one_per_resource": False}, #bibliographic editor
        ##{"nodeid": "c06e6773-95ef-11ea-8e2e-f875a44e0e11", "value_type": "author_name", "one_per_resource": False}, #bibliographic contributor
        #####digital objects??
        ##{"nodeid": "c5c43d8c-eecc-11eb-8a55-a87eeabdefba", "value_type": "file_name_pdf", "one_per_resource": False, "where_nodeid": "c5c43d8c-eecc-11eb-8a55-a87eeabdefba", "where_op":"contains", "where_value": "S:\\Exegesis"}, #digital object cross source where type is FILEPATH
        ##{"nodeid": "c747550a-eeca-11eb-9d91-a87eeabdefba", "value_type": "file_name_pdf", "one_per_resource": False, "where_nodeid": "c747550a-eeca-11eb-9d91-a87eeabdefba", "where_op":"contains", "where_value": "S:\\Exegesis"}, #digital object cross source where type is FILEPATH
        
        #monument
        #spatial meta data compilaer name
        #{"nodeid": "87d3c3fb-f44f-11eb-a313-a87eeabdefba", "value_type": "full_name", "one_per_resource": False}, #Full name
        #activity spatial meta data compilaer name
        #{"nodeid": "a5416b5c-f121-11eb-be96-a87eeabdefba", "value_type": "full_name", "one_per_resource": False}, #Full name

        ##{"nodeid": "c5c43d91-eecc-11eb-bb4c-a87eeabdefba", "value_type": "url", "one_per_resource": False, "where_nodeid": "2547c132-9505-11ea-b22f-f875a44e0e11", "where_op":"equals", "where_value": "0f466b8b-a347-439f-9b61-bee9811ccbf0"}, #digital object where type is URL
        ######delete using remove_resources command

        #"" FINDER NAME ARTEFACT
        ##{"nodeid": "40924a71-b536-11ea-88c3-f875a44e0e11", "value_type": "full_name", "one_per_resource": False},

        # Updater Name - activity and monument
        ##{"nodeid": "65229156-efc8-11eb-b16e-a87eeabdefba", "value_type": "full_name", "one_per_resource": False},
        ##{"nodeid": "6c219cbd-ee13-11eb-9e97-a87eeabdefba", "value_type": "full_name", "one_per_resource": False},
        ##{"nodeid": "87d3d7d4-f44f-11eb-ad91-a87eeabdefba", "value_type": "full_name", "one_per_resource": False},
        ##{"nodeid": "a541923e-f121-11eb-8237-a87eeabdefba", "value_type": "full_name", "one_per_resource": False},

        #Creator name - activity and monument
        ##{"nodeid": "65227d34-efc8-11eb-a018-a87eeabdefba", "value_type": "full_name", "one_per_resource": False},
        ##{"nodeid": "6c219c5c-ee13-11eb-ab86-a87eeabdefba", "value_type": "full_name", "one_per_resource": False},
    ]


    def obfuscate_node_values(self, subject_nodes=NODES_TO_CHANGE, index=True, force=False):
        """
        Runs the resource_remover command found in data_management.resources

        Args:
            graphid (str): the graphid of the resource model to be obfuscated
            nodeid list[str]: the nodeid of the node in tiles to obfuscate
            value_type (str): the type of value to be used for obfuscation. Options are "first_name", "last_name", "full_name", "email", "empty"
            index (bool): if True, the resource will be indexed after obfuscation. Defaults to True.

        """
        from arches.app.models.tile import Tile
        if not force:
            if not utils.get_yn_input(f"Nodes will be obfuscated with a random value. continue? "):
                return

        # get nodeids from subject_nodes
        nodeids = [subject_node["nodeid"] for subject_node in subject_nodes]
        print(f"Obfuscating {len(nodeids)} nodes")
        #nodes = models.Node.objects.filter(nodeid__in=nodeids).select_related("nodegroup")
                        
        #get all nodegroups from related nodes
        nodegroups = models.NodeGroup.objects.filter(node__nodeid__in=nodeids).distinct()
        print(f"Obfuscating {len(nodegroups)} nodegroups")

        #print distinct nodegroups ids
        for nodegroup in nodegroups:
            print(f"...nodegroup {nodegroup.nodegroupid}")   

        cache = {}
        tiles = Tile.objects.filter(nodegroup__in=nodegroups).select_related("resourceinstance")
        print(f"Obfuscating {len(tiles)} tiles...")
        transaction_id = uuid.uuid4()
        import pyprind, sys
        bar = pyprind.ProgBar(len(tiles), bar_char="█", stream=sys.stdout) if len(tiles) > 1 else None
        for tile in tiles:
            tile_dirty = False
            for subject_node in subject_nodes:             
                nodeid = subject_node["nodeid"]
                if nodeid in tile.data.keys():
                    if tile.data[nodeid] != "" and tile.data[nodeid] is not None: #then we need to edit the node value
                        
                        if tile.resourceinstance.resourceinstanceid not in cache.keys():
                            cache[tile.resourceinstance.resourceinstanceid] = self.generate_random_data_dict()

                        if subject_node["one_per_resource"]:
                            new_value = cache[tile.resourceinstance.resourceinstanceid][subject_node["value_type"]]
                        else:
                            new_value = self.generate_random_data_dict()[subject_node["value_type"]]
                        
                        if "where_nodeid" in subject_node.keys(): #if the node has a where clause we need to check that the where clause is true to edit the node value
                            if tile.data[subject_node["where_nodeid"]] is not None:
                                if subject_node["where_op"] == "contains":
                                    if subject_node["where_value"] in tile.data[subject_node["where_nodeid"]]:
                                        tile.data[nodeid] = new_value
                                        tile_dirty = True
                                elif subject_node["where_op"] == "equals":
                                    if tile.data[subject_node["where_nodeid"]] == subject_node["where_value"]:
                                        tile.data[nodeid] = new_value
                                        tile_dirty = True
                                else:
                                    raise Exception(f"where_op {subject_node['where_op']} not recognised")
                        else:
                            tile.data[nodeid] = new_value
                            tile_dirty = True
            
            if tile_dirty:
                tile.save(index=False,transaction_id=transaction_id)
            bar.update()

        
        rids = cache.keys()
        if index:
            print(f"Indexing {len(rids)} resources")
            index_resources_using_multiprocessing(rids,batch_size=250)


        print(f"Obfuscation complete")
        return

    def generate_random_data_dict(self):
        """
        Generates a random user dict

        Returns:
            dict: a dict of random user data with the following structure:

            {
                "title": "Mr",
                "title_id": "3cf16a39-594d-470c-9e9a-78139e9af77a", # valueid of the concept fo the given title (this is used for node value if concept)
                "first_name": "John",
                "last_name": "Smith",
                "full_name": "Mr John Smith",
                "email": "john.smith@example.com
                "full_address": "1 Main Street, Anytown, Anystate",
                "building_number": 1,
                "street": "Main Street",
                "city": "Anytown",
                "state": "Anystate",
                "author_name": "Smith, J",
                "phone_number": "01234 567890",
                "file_name": "C:\\aher\\1\\file1.txt",
                "file_name_pdf": "C:\\aher\\1\\file1.pdf",
                "file_name_docx": "C:\\aher\\1\\file1.docx",
                "file_name_doc": "C:\\aher\\1\\file1.doc",
                "file_name_txt": "C:\\aher\\1\\file1.txt",
                "url": "https://www.example.com/path/to/file.txt",
                "empty": ""
            }
        """
        import random

        
        title = random.choice([{
            "id": "3cf16a39-594d-470c-9e9a-78139e9af77a",
            "text": "Mr"
        },
        {
            "id": "67cf2d2d-de1c-4a59-8d27-941610d45256",
            "text": "Mrs"
        },
        {
            "id": "d030a719-5bc5-4fb8-a4df-96fb9781ad58",
            "text": "Ms"
        },
        {
            "id": "3101fcda-3119-4014-94ab-4fb4d7ef38db",
            "text": "Miss"
        }
        ])
        title_text = title["text"]
        title_id = title["id"]
        if title_text == "Mr":
            first_name = random.choice(self.MALE_FIRST_NAMES)
        else:
            first_name = random.choice(self.FEMALE_FIRST_NAMES)

        last_name = random.choice(self.LAST_NAMES)
        full_name = title_text + " " + first_name + " " + last_name
        email = first_name + "." + last_name + "@example.com"
        building_number = random.randint(1, 1000)
        street = random.choice(self.STREETS)
        city = random.choice(self.CITIES)
        state = random.choice(self.STATES)
        full_address = str(building_number) + " " + street + ", " + city + ", " + state
        file_name = self.create_random_file_path()
        file_name_pdf = self.create_random_file_path(extension=".pdf")
        file_name_docx = self.create_random_file_path(extension=".docx")
        file_name_doc = self.create_random_file_path(extension=".doc")
        file_name_txt = self.create_random_file_path(extension=".txt")
        url = self.create_random_url()
        
        
        return {
            "title": title_text,
            "title_id": title_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "email": email,
            "full_address": full_address,
            "building_number": building_number,
            "street": street,
            "city": city,
            "state": state,
            "author_name": last_name + ", " + first_name[0],
            "phone_number": "01234 567890",
            "file_name": file_name,
            "file_name_pdf": file_name_pdf,
            "file_name_docx": file_name_docx,
            "file_name_doc": file_name_doc,
            "file_name_txt": file_name_txt,
            "url": url,
            "empty": ""
        }

    def load_txt_file_into_list(self, file_path):
        """
        Loads a text file into a list of strings

        Args:
            file_path (str): the path to the file to be loaded

        Returns:
            list: a list of strings
        """
        value_list = []
        with open(file_path, "r") as f:
            value_list = f.read().splitlines()
        return value_list
    
    def create_random_file_path(self, extension=None):
        import random
        drive = random.choice(["C:", "D:", "E:", "F:", "\\\\server1\\share", "\\\\server2\\share2"])
        folder = random.choice(["\\aher\\1", "\\aher\\2", "\\aher\\3", "\\aher\\4"])
        file_name = random.choice(["\\file1", "\\file2", "\\file3", "\\file4"])
        file_extension = random.choice([".txt", ".doc", ".docx", ".pdf"]) if extension is None else extension
        return drive + folder + file_name + file_extension
    
    def create_random_url(self, isfile=False):
        import random
        host = random.choice(["https://www.example.org"])
        path = random.choice(["/path1", "/path2", "/path3", "/path4"])
        extension = random.choice(["/file.txt", "/file.doc", "/file.docx", "/file.pdf"]) if isfile else ""
        url = host + path + extension
        return url
    
    def create_example_url(self):
        return "https://www.example.com/path/to/file.txt"

    import os
    #THIS_FILES_PATH = os.path.dirname(os.path.realpath(__file__))
    THE_DIRECTORY_OF_THIS_FILE = os.path.dirname(os.path.realpath(__file__))
    MALE_FIRST_NAMES = load_txt_file_into_list(None, os.path.join(THE_DIRECTORY_OF_THIS_FILE,"random","male_first.txt"))
    FEMALE_FIRST_NAMES = load_txt_file_into_list(None, os.path.join(THE_DIRECTORY_OF_THIS_FILE,"random","female_first.txt"))
    LAST_NAMES = load_txt_file_into_list(None, os.path.join(THE_DIRECTORY_OF_THIS_FILE,"random","last.txt"))
    CITIES = load_txt_file_into_list(None, os.path.join(THE_DIRECTORY_OF_THIS_FILE,"random","cities.txt"))
    STREETS = load_txt_file_into_list(None, os.path.join(THE_DIRECTORY_OF_THIS_FILE,"random","street.txt"))
    STATES = load_txt_file_into_list(None, os.path.join(THE_DIRECTORY_OF_THIS_FILE,"random","states.txt"))

    
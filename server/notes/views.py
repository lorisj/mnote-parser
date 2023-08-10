from django.shortcuts import render
from django.http import HttpResponse
from neo4j import GraphDatabase
import subprocess
from rest_framework.views import APIView
from rest_framework.response import Response
import os # for testing

import configparser
import json as json 


# Create your views here.

class UpdateNotes(APIView):
    def get(self, request, format=None):
        try:
            #os.system("touch /home/loris/testfile.txt")
            # Change your directory path as needed
            A = subprocess.check_output(['git', '-C', '/home/loris/Notes/mnote-notefiles-public', 'pull'])
            # In the future find which paths to update

            # Process the output

            

            return Response({'status': 'success'}, status=200)
        except subprocess.CalledProcessError as e:
            # If the command fails, this will be executed
            return Response({'status': 'failure', 'error': str(e)}, status=500)
        
class DirectoryIndexer:
    def __init__(self, file_paths):
        # Extract unique last-second directories
        self.last_second_directories = {}
        index = 0
        for file_path in file_paths:
            # Extract the last-second directory
            last_second_directory = os.path.join(*os.path.normpath(file_path).split(os.path.sep)[-3:-1])
            # Assign an index if it's a new last-second directory
            if last_second_directory not in self.last_second_directories:
                self.last_second_directories[last_second_directory] = index
                index += 1

    def get_index(self, file_path):
        # Extract the last-second directory from the given file path
        last_second_directory = os.path.join(*os.path.normpath(file_path).split(os.path.sep)[-3:-1])
        # Return the index for the last-second directory
        return self.last_second_directories.get(last_second_directory, -1)


def get_color(index):
    colors = ["white","red", "blue", "green", "yellow", "purple", "orange", "pink", "brown", "gray", "black"]
    return colors[index % len(colors)]


def get_shape(type):
    #assert type in ["definition", "result", "example"]
    if type == "definition":
        return "square"
    elif type == "result":
        return "triangle"
    elif type == "example":
        return "dot"
    

def get_file_paths_list(starting_directory):
    out = []
    for root, dirs, files in os.walk(starting_directory):
        for file in files:
            if file.endswith('.mnote'):
                file_path = os.path.join(root, file)
                out.append(file_path)
    return out

def notes(request):
    file_paths_list = get_file_paths_list("/home/loris/Notes/mnote-notefiles-public")
    
    nodes, edges, edge_types = get_visualization_json_data(file_paths_list)
    context = {
        'nodes': nodes, 
        'edges': edges, 
        'edge_types': edge_types, 
        'file_paths_list' : file_paths_list
    }
    print(file_paths_list)
    return render(request, "template_vis_js.html", context)



def get_visualization_json_data(file_paths_list):

    directory_indexer = DirectoryIndexer(file_paths_list)
    # Connect to the database
    config = configparser.ConfigParser()
    config.read("/home/loris/.config/neo4j.ini")

    uri = config.get("neo4j", "uri")
    username = config.get("neo4j", "username")
    password = config.get("neo4j", "password")

    driver = GraphDatabase.driver(uri, auth=(username, password))
    

    with driver.session() as session:
        nodes_raw = session.run("MATCH (n) RETURN ID(n) as identity, labels(n) as labels, properties(n) as properties").data()
        edges_raw = session.run("MATCH ()-[r]->() RETURN ID(r) as identity, type(r) as type, properties(r) as properties, ID(startNode(r)) as start, ID(endNode(r)) as end").data()

        #Process edge types
        
        edge_types_result = session.run("CALL db.relationshipTypes()")
        edge_types = [record[0] for record in edge_types_result]
        edge_type_dict = {}
        for i, edge_type in enumerate(edge_types):
            edge_type_dict[edge_type] =  {'color': get_color(i)}


        # Process nodes
        nodes = []
        for node in nodes_raw:
            node_dict = {
                'id': node['identity'],
                'type': node['labels'][0], # definition, result, example
                'label': node['properties']["name"],
                'shape': get_shape(node['labels'][0]),
                'file' : node['properties']['filename'],
                'color' : get_color(directory_indexer.get_index(node['properties']['filename']))
            }
            nodes.append(node_dict)

        # Process edges
        edges = []
        for edge in edges_raw:
            edge_dict = {
                #'id': edge['identity'],
                'from': edge['start'],
                'to': edge['end'],
                'type': edge['type'],
                'arrows': 'to',
                'color': edge_type_dict[edge['type']]['color']
            }
            edges.append(edge_dict)
        
        
        

        # Convert nodes_transformed and edges_transformed to JSON format
        nodes = json.dumps(nodes)
        edges = json.dumps(edges)
        
    driver.close()
    return nodes, edges, edge_type_dict



if __name__ == "__main__":
    nodes, edges, edge_types = get_visualization_json_data()

    context = {
        'nodes': nodes,
        'edges': edges,
        'edge_types': edge_types
    }
    
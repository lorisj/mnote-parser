from django.shortcuts import render
from django.http import HttpResponse
from neo4j import GraphDatabase

import configparser
import json as json


# Create your views here.



def get_color(index):
    colors = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "brown", "gray", "black"]
    return colors[index % len(colors)]


def get_shape(type):
    #assert type in ["definition", "result", "example"]
    if type == "definition":
        return "square"
    elif type == "result":
        return "triangle"
    elif type == "example":
        return "dot"
    

def notes(request):

    
    nodes, edges, edge_types = get_visualization_json_data()
    context = {
        'nodes': nodes, 
        'edges': edges, 
        'edge_types': edge_types 
    }
    return render(request, "template_vis_js.html", context)



def get_visualization_json_data():
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
                'file' : "/category_theory/basics/category_theory_introduction.mnote"
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
    
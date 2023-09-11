from neo4j import GraphDatabase
from lark.tree import Tree
from lark import Token
from . import note_parser

#import note_parser
import configparser
import os as os
import argparse
from pathlib import Path

origin = "/home/loris/Notes/mnote-notefiles-public"

def create_nodes(tx, tree, filename, parent_name=None, parent_type=None):
    # Only process if this is a block
    if tree.data in ['definition', 'result', 'example']:
        # Use the block type as the node name
        name = tree.children[0].value

        # Create a node for this block
        tx.run(f"MERGE (n:{tree.data} {{name: $name, filename: $filename}}) RETURN n", name=name, filename=filename)

    # Recursively add all nodes from all child blocks
    for child in tree.children:
        if isinstance(child, Tree):
            create_nodes(tx, child, filename, parent_name=name if tree.data in ['definition', 'result', 'example'] else parent_name, parent_type=tree.data if tree.data in ['definition', 'result', 'example'] else parent_type)

def create_edges(tx, tree, filename, parent_name=None, parent_type=None):
    # Only process if this is a block
    if tree.data in ['definition', 'result', 'example']:
        # Use the block type as the node name
        name = tree.children[0].value
        if parent_name is not None and parent_type is not None:
            # If there's a parent, create a relationship between the parent and this block
            tx.run(f"""
            MATCH (a:{parent_type} {{name: $parent_name}})
            MATCH (b:{tree.data} {{name: $name}})
            MERGE (b)-[:IN_CONTEXT]->(a)
            """, parent_name=parent_name, name=name)
        if isinstance(tree.children[1], Tree) and tree.children[1].data == 'blockname_array': # Child specifies a context block array
            for related_node in tree.children[1].children:
                related_node_name = related_node.value  # get the name of the related node
                run_string = f"""
                MATCH (b:{tree.data} {{name: $name}})
                MATCH (d {{name: $related_node_name}}) 
                MERGE (b)-[:IN_CONTEXT]->(d)
                """
                tx.run(run_string, name=name, related_node_name=related_node_name, filename=filename) 
    # Recursively add edges from all child blocks
    for child in tree.children:
        if isinstance(child, Tree):
            create_edges(tx, child, filename, parent_name=name if tree.data in ['definition', 'result', 'example'] else parent_name, parent_type=tree.data if tree.data in ['definition', 'result', 'example'] else parent_type)

def store_nodes(tx, tree, filename, process_function):
    # Iterate over all children of the root of the tree
    
    filename =  filename.split(origin + "/",1)[1]

    for child in tree.children:
        # If the child is an instance of Tree class, recursively add it to the database
        if isinstance(child, Tree):
            process_function(tx,child,filename)
            

def mnote_process_file(tx, filepath, process_function):
    mnote_parser = note_parser.get_parser() # TODO: Use this to check if it compiles. If not, throw an error.
    # Get the file contents
    with open(filepath, 'r') as input_file:
        input_text = input_file.read()

        # Parse the file
        tree = mnote_parser.parse(input_text)

        # Add the tree to the database.
        store_nodes(tx, tree, filepath, process_function)

def traverse_and_process(tx, starting_directory):
    for root, dirs, files in os.walk(starting_directory): # First add all nodes
        for file in files:
            if file.endswith('.mnote'):
                print(file)
                file_path = os.path.join(root, file)
                mnote_process_file(tx, file_path, create_nodes)
    for root, dirs, files in os.walk(starting_directory): # Then add all edges
        for file in files:
            if file.endswith('.mnote'):
                file_path = os.path.join(root, file)
                mnote_process_file(tx, file_path, create_edges)
    for root, dirs, files in os.walk(starting_directory):
        for file in files:
            if file.endswith('.mnote'):
                file_path = Path(os.path.join(root, file))
                #os.system(f"touch {str(file_path.parent)}/{str(file_path.stem)}.DELETEME")
                cmd = (f"bash ~/Scripts/compile_current_mnote_file {str(file_path)}") # .mnote -> .tex
                os.system(cmd)
                cmd = (f"bash ~/Scripts/compile_current_tex_file") # .tex -> .pdf
                os.system(cmd)
                cmd = (f"mv ~/Temp/currentcompile/output.pdf {str(file_path.parent)}/{str(file_path.stem)}.pdf") # move pdf to github repo
                os.system(cmd)

def upload_client(starting_filepath):
    config = configparser.ConfigParser()
    config.read("/home/loris/.config/neo4j.ini") #TODO: CHANGEME

    uri = config.get("neo4j", "uri")
    username = config.get("neo4j", "username")
    password = config.get("neo4j", "password")

    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    with driver.session() as session:
        traverse_and_process(session, starting_filepath)

    driver.close()


def remove_client():
    config = configparser.ConfigParser()
    config.read("/home/loris/.config/neo4j.ini") #TODO: CHANGEME
    uri = config.get("neo4j", "uri")
    username = config.get("neo4j", "username")
    password = config.get("neo4j", "password")

    driver = GraphDatabase.driver(uri, auth=(username, password))
    with driver.session() as session:
        session.run("match(n) detach delete n")
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path', help='The path to the root file containing all .mnote files you want to process')
    args = parser.parse_args()

    
    starting_filepath = args.file_path
    upload_client(starting_filepath)


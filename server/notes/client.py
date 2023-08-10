from neo4j import GraphDatabase
from lark.tree import Tree
from lark import Token
from note_parser import get_parser
import configparser
import os as os
import argparse

def add_tree(tx, tree, filename, parent_name=None, parent_type=None):
    # Only process if this is a block
    if tree.data in ['definition', 'result', 'example']:
        # Use the block type as the node name
        name = tree.children[0].value

        # Create a node for this block
        tx.run(f"MERGE (n:{tree.data} {{name: $name, filename: $filename}}) RETURN n", name=name, filename=filename)

        if parent_name is not None and parent_type is not None:
            # If there's a parent, create a relationship between the parent and this block
            tx.run(f"""
            MATCH (a:{parent_type} {{name: $parent_name}})
            MATCH (b:{tree.data} {{name: $name}})
            MERGE (b)-[:IN_CONTEXT]->(a)
            """, parent_name=parent_name, name=name)
        if isinstance(tree.children[1], Token) and tree.children[1].type == 'BLOCKNAME': # Child specifies a context block
            related_node_name = tree.children[1].value  # get the name of the related node
            tx.run(f"""
            MATCH (b:{tree.data} {{name: $name}})
            MATCH (d:definition {{name: $related_node_name, filename: $filename}})
            MERGE (b)-[:IN_CONTEXT]->(d)
            """, name=name, related_node_name=related_node_name, filename=filename) # MATCH DEFINTIONS
            tx.run(f"""
            MATCH (b:{tree.data} {{name: $name}})
            MATCH (d:result {{name: $related_node_name, filename: $filename}})
            MERGE (b)-[:IN_CONTEXT]->(d)
            """, name=name, related_node_name=related_node_name, filename=filename) # MATCH RESULTS
            tx.run(f"""
            MATCH (b:{tree.data} {{name: $name}})
            MATCH (d:example {{name: $related_node_name, filename: $filename}})
            MERGE (b)-[:IN_CONTEXT]->(d)
            """, name=name, related_node_name=related_node_name, filename=filename) #MATCH EXAMPLES
    # Recursively add all child blocks
    for child in tree.children:
        if isinstance(child, Tree):
            add_tree(tx, child, filename, parent_name=name if tree.data in ['definition', 'result', 'example'] else parent_name, parent_type=tree.data if tree.data in ['definition', 'result', 'example'] else parent_type)

def store_tree(tx, tree, filename):
    # Iterate over all children of the root of the tree
    for child in tree.children:
        # If the child is an instance of Tree class, recursively add it to the database
        if isinstance(child, Tree):
            add_tree(tx, child, filename)


def process_mnote_file(tx, filepath):
    # Get the file contents
    with open(filepath, 'r') as input_file:
        input_text = input_file.read()

        # Parse the file
        tree = mnote_parser.parse(input_text)

        # Get the root of the tree.
        root = tree.children[0]  # Adjust this line as necessary based on the structure of your tree.

        # Add the tree to the database.
        store_tree(tx, tree, filepath)
def traverse_and_process(tx, starting_directory):
    for root, dirs, files in os.walk(starting_directory):
        for file in files:
            if file.endswith('.mnote'):
                file_path = os.path.join(root, file)
                process_mnote_file(tx, file_path)
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path', help='The path to the input file')
    args = parser.parse_args()

    
    starting_filepath = args.file_path

    config = configparser.ConfigParser()
    config.read("/home/loris/.config/neo4j.ini")

    uri = config.get("neo4j", "uri")
    username = config.get("neo4j", "username")
    password = config.get("neo4j", "password")

    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    with driver.session() as session:
        #starting_filepath = "/home/loris/Notes/mnote-notefiles-public"
        
        mnote_parser = get_parser()
        
        traverse_and_process(session, starting_filepath)


    driver.close()


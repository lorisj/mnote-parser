from neo4j import GraphDatabase
from lark.tree import Tree
from lark import Token
from note_parser import get_parser

def add_tree(tx, tree, parent_name=None, parent_type=None):
    # Only process if this is a block
    if tree.data in ['definition', 'result', 'example']:
        # Use the block type as the node name
        name = tree.children[0].value

        # Create a node for this block
        tx.run(f"MERGE (n:{tree.data} {{name: $name}}) RETURN n", name=name)

        if parent_name is not None and parent_type is not None:
            # If there's a parent, create a relationship between the parent and this block
            tx.run(f"""
            MATCH (a:{parent_type} {{name: $parent_name}})
            MATCH (b:{tree.data} {{name: $name}})
            MERGE (b)-[:IN_CONTEXT]->(a)
            """, parent_name=parent_name, name=name)
            
        if isinstance(tree.children[1], Token) and tree.children[1].type == 'BLOCKNAME':
            related_node_name = tree.children[1].value  # get the name of the related node
            tx.run(f"""
            MATCH (b:{tree.data} {{name: $name}})
            MATCH (d:{Token('RULE', 'definition')} {{name: $related_node_name}})
            MERGE (b)-[:IN_CONTEXT]->(d)
            """, name=name, related_node_name=related_node_name) # MATCH DEFINTIONS
            tx.run(f"""
            MATCH (b:{tree.data} {{name: $name}})
            MATCH (d:{Token('RULE', 'result')} {{name: $related_node_name}})
            MERGE (b)-[:IN_CONTEXT]->(d)
            """, name=name, related_node_name=related_node_name) # MATCH RESULTS
            tx.run(f"""
            MATCH (b:{tree.data} {{name: $name}})
            MATCH (d:{Token('RULE', 'example')} {{name: $related_node_name}})
            MERGE (b)-[:IN_CONTEXT]->(d)
            """, name=name, related_node_name=related_node_name) #MATCH EXAMPLES

    # Recursively add all child blocks
    for child in tree.children:
        if isinstance(child, Tree):
            add_tree(tx, child, parent_name=name if tree.data in ['definition', 'result', 'example'] else parent_name, parent_type=tree.data if tree.data in ['definition', 'result', 'example'] else parent_type)

def store_tree(tx, tree):
    # Iterate over all children of the root of the tree
    for child in tree.children:
        # If the child is an instance of Tree class, recursively add it to the database
        if isinstance(child, Tree):
            add_tree(tx, child)

if __name__ == '__main__':
    uri = "bolt://localhost:7687"

    driver = GraphDatabase.driver(uri, auth=("neo4j", "testpassword"))

    with driver.session() as session:
        file_path = "/home/loris/Projects/structured_notes/examples/category_theory_introduction.mnote"

        mnote_parser = get_parser()
        
        with open(file_path, 'r') as input_file:
            input_text = input_file.read()
            
            tree = mnote_parser.parse(input_text)
            # print(tree.pretty())
            # exit()

        
            # Get the root of the tree.
            root = tree.children[0]  # Adjust this line as necessary based on the structure of your tree.

            # Add the tree to the database.
            session.execute_write(store_tree, tree)

    driver.close()


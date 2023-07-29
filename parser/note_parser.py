from lark import Lark
from lark.indenter import Indenter

from lark import Lark, v_args
from lark import Transformer
from lark.visitors import Interpreter


import argparse


block_grammer = r"""
    start: content*

    content: (text | block)

    block: (definition | result | example)

    result: ("%res(" BLOCKNAME "):")  _NL [_INDENT content* _DEDENT] 
    example: ("%exp(" BLOCKNAME "):")  _NL [_INDENT content* _DEDENT]
    definition: ("%def(" BLOCKNAME "):") _NL [_INDENT content* _DEDENT]

"""



# Text grammar, i.e. simplifying LaTeX structure. Remember that string has the form:"this is a string, it contains the quotes"
text_grammar = r"""
    text: (line | tex_block | empty_line) +
    line: (_WS* STRING  _NL?) 
    empty_line: _WS* _NL
    tex_block: enumerate | itemize | nice_equation | equation #| image
    enumerate: "%enum" _NL [_INDENT item* _DEDENT]
    itemize: "%item" _NL [_INDENT item* _DEDENT]
    nice_equation: "%neq" _NL [_INDENT line+ _DEDENT]
    equation: "%eq" _NL [_INDENT line+ _DEDENT]
    item: "%i" _WS text
    STRING:  /[^%\n]+/
    _WS: /[\t ]+/
"""

symbol_grammar =r"""
    BLOCKNAME: /[a-zA-Z0-9_]+/
    %declare _INDENT _DEDENT
    _NL: /(\r?\n[\t ]*)/
"""

class TreeIndenter(Indenter):
    NL_type = '_NL'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 4



class MyInterpreter(Interpreter):
    def ind_print(self, string_in):
        print('\t' * self.indent_level, end='')
        print(string_in)
    
    def tex_block_print(self, type, tree):
        self.ind_print("\\begin{" + type + "}")
        self.indent_level += 1
        for child in tree.children:
            self.visit(child)
        self.indent_level -= 1
        self.ind_print("\\end{" + type + "}")

    def __init__(self):
        super().__init__()
        self.indent_level = 0

    def start(self, tree):
        for child in tree.children:
            self.visit(child)
        print() # Ensure we end with a newline

    def content(self, tree):
        for child in tree.children:
            self.visit(child)
           

    def block(self, tree):
        #self.indent_level += 1
        self.visit(tree.children[0])
        #self.indent_level -= 1
        print()

    def result(self, tree):
        self.boxed_object("result", tree)

    def example(self, tree):
        self.boxed_object("example", tree)

    def definition(self, tree):
        self.boxed_object("definition", tree)
    def STRING(self, token):
        print("STRING")
    def text(self, tree):
        for child in tree.children:
            self.visit(child)

    def line(self, tree):
        self.ind_print(tree.children[0])

    def tex_block(self, tree):
        
        self.visit(tree.children[0])
        
    def enumerate(self, tree):
        self.tex_block_print("enumerate", tree)
        

    def itemize(self, tree):
        self.tex_block_print("itemize", tree)

    def item(self, tree):
        self.ind_print("\\item")
        self.visit(tree.children[0])

    def nice_equation(self, tree):
        self.tex_block_print("niceeq", tree)

    def equation(self, tree):
        self.tex_block_print("equation", tree)

    def boxed_object(self, type, tree):
        name = tree.children[0]
        content_list = tree.children[1:]
        self.ind_print("\\begin{" + type + "}{" + name + "}{" + name + "}")
        self.indent_level += 1
        for child in content_list:
            self.visit(child)
        self.indent_level -= 1
        self.ind_print("\\end{" + type + "}")










full_grammar = block_grammer + text_grammar + symbol_grammar 



#transformed_parser = Lark(full_grammar, parser='lalr', postlex=TreeIndenter(), transformer=MyTransformer())
test_parser = Lark(full_grammar, parser='lalr', postlex=TreeIndenter())


test_input_text=r"""next line will be empty

after the empty line
%def(vector_space):
    this is the def of a vector space
    this is the second line
    %res(key_theorem):
        Key theorem of linear algebra goes here
        %enum
            %i this is the first item
            %i this is the second item
            this is the second line of the second item
            %eq
                \sum_{i=1}^{n}{a}\\
        Now is more text after  
"""     

def test():

    tree = test_parser.parse(test_input_text)
    interpreter = MyInterpreter()
    interpreter.visit(tree)
    print(tree.pretty())



    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path', help='The path to the input file')
    args = parser.parse_args()

    
    file_path = args.file_path
    
    mnote_parser = Lark(full_grammar, parser='lalr', postlex=TreeIndenter())

    with open(file_path, 'r') as input_file:
        input_text = input_file.read()
        print(input_text == test_input_text)
        print(input_text)

        tree = mnote_parser.parse(input_text)
        interpreter = MyInterpreter()
        interpreter.visit(tree)



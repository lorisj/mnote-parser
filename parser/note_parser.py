from lark import Lark
from lark.indenter import Indenter

from lark import Lark, v_args
from lark import Transformer
from lark.visitors import Interpreter


import argparse


block_grammer = r"""
    start: (content | section_name)*

    section_name: _WS* "#" /[^%\n]+/ _NL

    content: (text | block)

    block: (definition | result | example | proof)

    result: _WS* ("%res(" BLOCKNAME ")") ("["BLOCKNAME"]")? _WS*_NL [_INDENT content* _DEDENT] 
    example: _WS*  ("%exp(" BLOCKNAME ")") ("["BLOCKNAME"]")? _WS*_NL [_INDENT content* _DEDENT]
    definition: _WS*  ("%def(" BLOCKNAME ")")("["BLOCKNAME"]")? _WS*_NL [_INDENT content* _DEDENT]
    proof: _WS* ("%pf") _WS* _NL [_INDENT content* _DEDENT]

"""


# Text grammar, i.e. simplifying LaTeX structure. Remember that string has the form:"this is a string, it contains the quotes"
text_grammar = r"""
    text: (line | tex_block | empty_line | line_command) +

    line_command: (dline | subtitle | image)
    line: (_WS* STRING inline_command? STRING?  _NL?) 
    inline_command: block_reference #| bib_reference
    block_reference: _WS* "%ref(" BLOCKNAME ")" _WS*

    empty_line: _WS* _NL
    tex_block: enumerate | itemize | nice_equation | equation #| image
    enumerate:_WS* "%enum" _WS* _NL [_INDENT item* _DEDENT]
    itemize: _WS*"%item" _WS* _NL [_INDENT item* _DEDENT]
    nice_equation: _WS*"%neq" _WS*_NL [_INDENT line+ _DEDENT]
    equation: _WS*"%eq" _WS* _NL [_INDENT line+ _DEDENT]
    item: "%i" _WS? content*

    dline: _WS* "%dl" _NL?
    subtitle: _WS* "%st(" BLOCKNAME ")" _NL?
    image: _WS* "%img(" BLOCKNAME ")" _NL?

    STRING:  /[^%#\n]+/
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

def title_case(title: str) -> str:
    minor_words = ["as", "at", "by", "in", "of", "off", "on", "per", "to", "up", "via", "the", "and", "but", "for", "if", "nor", "or", "so", "yet", "a", "an"]
    words = title.split()
    title_cased_words = []
    for i, word in enumerate(words):
        if i == 0 or i == len(words) - 1 or word.lower() not in minor_words:
            title_cased_words.append(word.capitalize())
        else:
            title_cased_words.append(word.lower())
    return " ".join(title_cased_words)


def format_name(name: str) -> str:
    
    name = name.replace("_", " ")
    name = title_case(name)
    return name
class MyInterpreter(Interpreter):
    def ind_println(self, string_in):
        print('\t' * self.indent_level, end='')
        print(string_in)
        
    def ind_print(self, string_in):
        print('\t' * self.indent_level, end='')
        print(string_in, end='')
    
    def tex_block_print(self, type, tree):
        self.ind_println("\\begin{" + type + "}")
        self.indent_level += 1
        for child in tree.children:
            self.visit(child)
        self.indent_level -= 1
        self.ind_println("\\end{" + type + "}")


    def block_reference(self, tree): # TODO: Communicates with server.
        print("\\refdef{" + format_name(tree.children[0]) + "}", end="") # TODO: Change this to either link. Local reference with %lref
    
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
        for child in tree.children:
            self.visit(child)

    def result(self, tree):
        self.boxed_object("result", tree)

    def example(self, tree):
        self.boxed_object("example", tree)

    def definition(self, tree):
        self.boxed_object("definition", tree)
    
    def text(self, tree):
        for child in tree.children:
            self.visit(child)
    def dline(self, tree):
        self.ind_println("\\dline")

    def proof(self, tree):
        self.tex_block_print("proof", tree)

    def line(self, tree):
        self.ind_print("")
        for child in tree.children:
            if isinstance(child, str):
                print(child, end="")
            else: # Handle inline commands,
                self.visit(child)
        print() # get newline at end.

    def subtitle(self, tree):
        self.ind_println("\\subtitle{" + format_name(tree.children[0]) + "}")
    
    def section_name(self, tree):
        number_pound_signs = tree.children[0].count("#")
        name_without_pound_signs = format_name(tree.children[0].replace("#", "").strip())
        if number_pound_signs == 0:
            self.ind_println("\\section{" + name_without_pound_signs + "}")
        elif number_pound_signs == 1:
            self.ind_println("\\subsection{" + name_without_pound_signs + "}")
        else: # raise error, too many pound signs
            raise ValueError("Too many pound signs in section name")
            
    def empty_line(self, tree):
        self.ind_println("")

    def tex_block(self, tree):
        for child in tree.children:
            self.visit(child)
        
    def enumerate(self, tree):
        self.tex_block_print("enumerate", tree)

    def itemize(self, tree):
        self.tex_block_print("itemize", tree)

    def item(self, tree):
        self.ind_println("\\item")
        for child in tree.children:
            self.visit(child)

    def nice_equation(self, tree):
        self.tex_block_print("niceeq", tree)

    def equation(self, tree):
        self.tex_block_print("algin", tree) # we call equations align, as this allows multi-line equations

    def boxed_object(self, type, tree):
        
        content_list = tree.children[1:]
        name = ""

        if isinstance(tree.children[1], str):
            content_list = tree.children[2:]
            name = f"(in {tree.children[1]}) "# keep space here
        name+= tree.children[0]
        name = format_name(name)

        self.ind_println("\\begin{" + type + "}{" + name + "}{" + name + "}")
        self.indent_level += 1
        for child in content_list:
            self.visit(child)
        self.indent_level -= 1
        self.ind_println("\\end{" + type + "}")



full_grammar = block_grammer + text_grammar + symbol_grammar 


latex_start_text = r"""\documentclass[12pt]{article}
\usepackage{notespkg}
\usepackage{screenread} %Puts every document on one page comment out if not needed.
%\addbibresource{bibliography.bib} % Rename bibliography.bib to your current .bib file, in the same directory. 
\usepackage{categorytheory}
\title{\currfilebase} % \currfilebase removes the .tex
\author{Loris Jautakas}
\begin{document}
\maketitle

%\tableofcontents
"""

latex_end_text = r"""\end{document}"""
#transformed_parser = Lark(full_grammar, parser='lalr', postlex=TreeIndenter(), transformer=MyTransformer())
test_parser = Lark(full_grammar, parser='lalr', postlex=TreeIndenter())


def get_parser():
    return Lark(full_grammar, parser='lalr', postlex=TreeIndenter())

    
if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument('file_path', help='The path to the input file')
    # args = parser.parse_args()

    
    # file_path = args.file_path

    file_path = "/home/loris/Projects/structured_notes/examples/category_theory_introduction.mnote"
    
    mnote_parser = get_parser()

    with open(file_path, 'r') as input_file:
        input_text = input_file.read()
        
        tree = mnote_parser.parse(input_text)
        interpreter = MyInterpreter()
        
        print(tree.pretty())
        exit()
        print(latex_start_text)
        
        interpreter.visit(tree)
        print(latex_end_text)




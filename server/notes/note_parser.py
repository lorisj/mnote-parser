from lark import Lark
from lark.indenter import Indenter
from lark import Lark, v_args
from lark import Transformer
from lark.visitors import Interpreter
from pathlib import Path


import argparse


block_grammer = r"""
    start: (content | section_name)*

    section_name: _WS* "#" /[^%\n]+/ _NL?

    content: (text | block)

    block: (definition | result | example | proof)

    result: _WS* ("%res(" BLOCKNAME ")") (blockname_array)? _WS*_NL [_INDENT content* _DEDENT] 
    example: _WS*  ("%exp(" BLOCKNAME ")") (blockname_array)? _WS*_NL [_INDENT content* _DEDENT]
    definition: _WS*  ("%def(" BLOCKNAME ")")(blockname_array)? _WS*_NL [_INDENT content* _DEDENT]
    proof: _WS* ("%pf") _WS* _NL [_INDENT content* _DEDENT]

    blockname_array: "["BLOCKNAME (","_WS* BLOCKNAME)* "]"
"""


# Text grammar, i.e. simplifying LaTeX structure.
text_grammar = r"""
    text: (line | tex_block | empty_line | line_command) +

    line_command: (dline | subtitle | image | todoline | newpage)_WS* _NL?
    line: (_WS* STRING inline_command? STRING?  _NL?)  # Need the ? in _NL? to handle the case where there is no newline at the end of the file.
    inline_command: block_reference #| bib_reference
    block_reference: _WS* "%ref(" BLOCKNAME ")" _WS*

    empty_line: _WS* _NL
    tex_block: enumerate | itemize | nice_equation | equation | tikcd | tikcd_center
    enumerate:_WS* "%enum" _WS* _NL [_INDENT item+ _DEDENT]
    tikcd: _WS* "%cd" _WS* _NL [_INDENT text _DEDENT]    
    tikcd_center: _WS* "%ccd" _WS* _NL [_INDENT text _DEDENT]
    itemize: _WS*"%item" _WS? _NL [_INDENT item+ _DEDENT]
    nice_equation: _WS*"%neq" _WS*_NL [_INDENT text _DEDENT]
    equation: _WS*"%eq" _WS* _NL [_INDENT text _DEDENT]
    item: "%i" _WS? content*
    
    dline: _WS* "%dl"
    newpage: _WS* "%np"
    subtitle: _WS* "%st(" BLOCKNAME ")" 
    todoline: _WS* "%todo" STRING 
    image: _WS* "%img(" filepath ("%s("/\d\d?\d?/")")? ")" _WS*
    
"""

symbol_grammar =r"""
    STRING:  /[^%#\n]+/
    _WS: /[\t ]+/
    LINK: /\[[^\]]+\]\([^\)]+\)/
    BLOCKNAME: /[a-zA-Z0-9][a-zA-Z0-9_"\-]*/
    %declare _INDENT _DEDENT
    _NL: /(\r?\n[\t ]*)/
    filepath: /\/([a-zA-Z0-9\-\.\/_]+)\.\w{1,4}/
    link: /(http(s)?:\/\/)?(www\.)?[a-zA-Z0-9\-\.]+/ filepath
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
            title_cased_words.append(word)
    return " ".join(title_cased_words)

def escape_underscore(string: str) -> str:
    return string.replace("_", "\_")

def replace_underscore(string: str) -> str:
    return string.replace("_", " ")

def format_name(name: str) -> str:
    name = replace_underscore(name)
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


    def block_reference(self, tree): # TODO: make sure this communicates with server to get block text.
        print("\\refdef{" + tree.children[0] + "}", end="") # TODO: Change this to either link. Local reference with %lref
    
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
    def newpage(self, tree):
        self.ind_println("\\newpage")
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
    def todoline(self, tree):
        self.ind_println("\\todo[inline]{" + tree.children[0] + "}")

    def image(self, tree):
        file_path = Path(str(tree.children[0].children[0])) # TODO: Figure out a way to have a database of images, and a way to upload images.
    
        self.ind_println("\\begin{figure}[h]")
        self.indent_level += 1
        self.ind_println("\\centering")
        if(file_path.suffix == ".svg"):
            self.ind_println("\\includesvg{" + str(file_path) +"}")
        else:
            self.ind_println("\\includegraphics{" + file_path +"}")
        self.ind_println("\\caption{" + format_name(file_path.stem) + "}")
        self.indent_level -= 1
        self.ind_println("\\end{figure}")
        

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
    
    def tikcd(self, tree):
        self.tex_block_print("tikzcd", tree)

    def tikcd_center(self, tree):
        self.ind_println("\\begin{center}")
        self.indent_level += 1
        self.tex_block_print("tikzcd", tree)
        self.indent_level -= 1
        self.ind_println("\\end{center}")

    def itemize(self, tree):
        self.tex_block_print("itemize", tree)

    def item(self, tree):
        self.ind_println("\\item")
        for child in tree.children:
            self.visit(child)

    def nice_equation(self, tree):
        self.tex_block_print("niceeq", tree)

    def equation(self, tree):
        self.tex_block_print("align", tree) # we call equations align, as this allows multi-line equations

    def boxed_object(self, type, tree):
        content_list = tree.children[1:]
        tag_name = tree.children[0]
        name = ""
        if tree.children[1].data == "blockname_array":
            content_list = tree.children[2:]
            context_array = [f"{str(child)}" for child in tree.children[1].children]
            name = escape_underscore(f"{str(context_array)}/ \\\\")
        else:
            name += "/"
        name+= escape_underscore(tag_name)#format_name(tag_name)

        self.ind_println("\\begin{" + type + "}{" + name.replace("'", "") + "}{" + escape_underscore(tag_name) + "}")
        self.indent_level += 1
        for child in content_list:
            self.visit(child)
        self.indent_level -= 1
        self.ind_println("\\end{" + type + "}")



full_grammar = block_grammer + text_grammar + symbol_grammar 


def get_start_text(file_name : str) -> str:
    latex_start_text = r"""\documentclass[12pt]{article}
\usepackage{notespkg}
\usepackage{screenread} %Puts every document on one page comment out if not needed.
%\addbibresource{bibliography.bib} % Rename bibliography.bib to your current .bib file, in the same directory. 
\usepackage{categorytheory}
\usepackage{probability}
\usepackage{quantuminfo}
\usepackage{settheory}
\usepackage{topology}
\usepackage{linalg}
\title{""" +  file_name + r"""} % \currfilebase removes the .tex
\author{Loris Jautakas}
\begin{document}
\maketitle

%\tableofcontents
"""
    return latex_start_text

latex_end_text = r"""\end{document}"""
#transformed_parser = Lark(full_grammar, parser='lalr', postlex=TreeIndenter(), transformer=MyTransformer())
test_parser = Lark(full_grammar, parser='lalr', postlex=TreeIndenter())


def get_parser():
    return Lark(full_grammar, parser='lalr', postlex=TreeIndenter())
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path', help='The path to the input file')
    args = parser.parse_args()

    
    file_path = Path(args.file_path)

    #file_path = "/home/loris/Notes/mnote-notefiles-public/set_theory/functions_and_relations.mnote"
    
    mnote_parser = get_parser()

    with open(file_path, 'r') as input_file:
        input_text = input_file.read()
        
        tree = mnote_parser.parse(input_text)
        interpreter = MyInterpreter()
        
        # print(tree.pretty()) # PRINT TREE STRUCTURE
        # exit()
        print(get_start_text(format_name(file_path.stem)))
        
        interpreter.visit(tree)
        print(latex_end_text)
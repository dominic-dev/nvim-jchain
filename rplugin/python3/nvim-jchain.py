import abc
import neovim
import glob
import os
import re

INDENT_CHAR = "    "

@neovim.plugin
class Main(object):
    def __init__(self, nvim):
        self.nvim = nvim

    @neovim.function('ChainConstructor')
    def chainConstructor(self, args):
        buff = self.nvim.current.buffer
        row, col = self.nvim.current.window.cursor
        directory, filename_long = os.path.split(self.nvim.eval("@%"))
        filename_short, extension = os.path.splitext(filename_long)
        class_name = filename_short.title()

        current_constructor = Constructor.get_current_constructor(row,\
                                                   class_name, buff)
        constructors = Constructor.get_all_constructors(class_name, buff)
        constructors.remove(current_constructor)

        if not constructors:
            return
        # Default to first item
        index = 0
        # Prompt if there are more items
        if len(constructors) > 1:
            # Join the constructors as choices, add an ordinal
            # and filter no-arg constructor from choices
            choices = "\n&".join(["{}. {}".format(i+1, str(r)[5:-2]) for i, r in\
                      enumerate(constructors) if r.text != "this();"])
            self.nvim.command('call inputsave()')
            command = "let user_input = confirm('Choose a constructor to chain', '&{}', 1)".format(choices)
            self.nvim.command(command)
            self.nvim.command('call inputrestore()')
            index = self.nvim.eval('user_input') - 1
            # Cancel in vim
            if index == -1:
                return

        result = str(constructors[index])
        # Indentation
        indentation = buff[row-1].count(INDENT_CHAR)
        if 'public' in buff[row-1]:
            indentation += 1
        # Append result
        buff.append((INDENT_CHAR * indentation) + result, row)


class Constructor:
    def __init__(self, class_name, line=None):
        self.class_name = class_name
        self.text = ""
        if line:
            self.text = self.parse(line)

    def parse(self, line):
        """
        Take a line, return the string to call the constructor
        """
        pattern = r"public " + re.escape(self.class_name) + r"\(((\w+ \w+(, |\)))*)"
        prog = re.compile(pattern)
        match = prog.search(line)
        if match:
            if match.group(1):
                arguments = match.group(1)\
                                .replace(')', '')\
                                .split(',')
                # Filter out variable names
                variable_names = [argument.strip().split(" ")[1] for argument in arguments]
            else:
                variable_names = []
            return "this({});".format(", ".join(variable_names))

    @staticmethod
    def get_current_constructor(row, class_name, text):
        return Constructor._get_constructors_from_text(class_name, text, row,
                                    end=0, step=-1, first_match_only=True)
        pattern = r"public " + re.escape(class_name)
        # pattern = r"public \w*(((\w+ \w+(, |\)))+)"
        # pattern = r"public " + re.escape(class_name) +  r"(((\w+ \w+(, |\)))+)"
        prog = re.compile(pattern)
        current_constructor = None
        start = 7
        while current_constructor is None:
            if prog.search(text[row]):
                line = text[row]
                # return line#[row_pos].strip()[start:]
                return Constructor(class_name, line)
            if row == 0:
                return
            row -= 1

    @staticmethod
    def get_all_constructors(class_name, text):
        return Constructor._get_constructors_from_text(class_name, text)

    @staticmethod
    def _get_constructors_from_text(class_name, text, start=0, end=None,
                                    step=1, first_match_only=False):
        if end is None:
            end = len(text)
        pattern = r"public " + re.escape(class_name)
        prog = re.compile(pattern)

        result = []
        row = start
        while row != end:
            if prog.search(text[row]):
                constructor = Constructor(class_name, text[row])
                if first_match_only:
                    return constructor
                result.append(constructor)
            row += step
        return result


    def __str__(self):
        return self.text

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.text == other.text
        return False

import abc
import neovim
import glob
import os
import re

@neovim.plugin
class Main(object):
    def __init__(self, nvim):
        self.nvim = nvim

    @neovim.function('ChainConstructor')
    def chainConstructor(self, args):
        buff = self.nvim.current.buffer
        row, col = self.nvim.current.window.cursor
        line = buff[row-1]
        filename_long = self.nvim.eval("expand('%:t')")
        filename_short, extension = os.path.splitext(filename_long)
        class_name = filename_short.title()

        # Settings
        try:
            include_noargs = self.nvim.eval("g:jchain_include_noargs")
        except:
            include_noargs = False

        # Get constructors
        current_constructor = Constructor.get_current_constructor(row,\
                                                   class_name, buff)
        constructors = Constructor.get_all_constructors(class_name, buff,\
                                                    include_noargs=include_noargs)
        if current_constructor.text != 'this();':
            constructors.remove(current_constructor)

        # If no matches remain
        if not constructors:
            return

        # Default to first item
        index = 0
        # Prompt if there are more items
        if len(constructors) > 1:
            # Join the constructors as choices, add an ordinal
            choices = "\n&".join(["{}. {}".format(i+1, r.preview)\
                          for i, r in enumerate(constructors)])
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
        indentation = get_indentation(line)
        # Append result
        buff.append(indentation + result, row)

class Constructor:
    def __init__(self, class_name, line=None):
        self.class_name = class_name
        self.text = ""
        if line:
            self.text = self.parse(line)
            self.preview = self.parse_preview(line)


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

    def parse_preview(self, line):
        """
        Take a line, return a preview string of the constructor
        """
        # remove 'this(' at the beginning and ');' at the end
        begin = 5
        end = -2
        if self.text:
            return self.text[begin:end]
        return self._parse(line)[begin:end]

    @staticmethod
    def get_current_constructor(row, class_name, text):
        """
        Return the current cunstructor, under cursor
        Arguments:
            row (int) the row number of the cursor
            class_name (str) the name of the class that is constructed
            text (str) the text to search
        """
        return Constructor._get_constructors_from_text(class_name, text, row,
                                    end=0, step=-1, first_match_only=True)
        pattern = r"public " + re.escape(class_name)
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
    def get_all_constructors(class_name, text, include_noargs=False):
        result = Constructor._get_constructors_from_text(class_name, text)
        if not include_noargs:
            result = [r for r in result if r.text != 'this();']
        return result

    @staticmethod
    def _get_constructors_from_text(class_name, text, start=0, end=None,
                                    step=1, first_match_only=False):
        """
        Take text and return constructors
        Arguments:
            class_name (str) the name of the class that is constructed
            text (str) the text to search in
            start (int) the first line to search
            end (int) the last line to search
            step (int) the number by which to iterate over the lines
            first_match_only (bool) return only the first match if true
        """
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

def get_indentation(line):
    """
    Take a line, and return its indentation as string
    """
    pattern = re.compile(r"(.*?)\w")
    match = pattern.search(line)
    if not match:
        return
    indentation = match.group(1)
    if "public" in line:
        return indentation + indentation
    return indentation


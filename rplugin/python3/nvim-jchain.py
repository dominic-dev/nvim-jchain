import abc
import neovim
import glob
import os
import re

@neovim.plugin
class Main(object):
    def __init__(self, nvim):
        self.nvim = nvim

    def _get_context(self):
        buff = self.nvim.current.buffer
        row, col = self.nvim.current.window.cursor
        return (buff, row)

    def _get_current_line(self):
        buff, row = self._get_context()
        return buff[row-1]

    def _get_directory(self):
        return self.nvim.eval("expand('%:p:h')")

    def _get_class_name(self):
        filename_long = self.nvim.eval("expand('%:t')")
        filename_short, extension = os.path.splitext(filename_long)
        return filename_short.title()


    @neovim.function('ChainConstructor')
    def chainConstructor(self, args):
        """
        Insert the call to another constructor
        Prompt if there is more than one match.
        """
        buff, row = self._get_context()
        class_name = self._get_class_name()

        # Settings
        try:
            include_noargs = self.nvim.eval("g:jchain_include_noargs")
        except:
            include_noargs = False
        # Get constructors
        current_constructor = Constructor.get_current_constructor(row,\
                                           class_name, buff)
        if not current_constructor:
            return;
        constructors = Constructor.get_all_constructors(class_name, buff,\
                                                include_noargs=include_noargs)
        if current_constructor.text != 'this();':
            constructors.remove(current_constructor)
        self.return_constructors(constructors, current_constructor)


    @neovim.function('GenerateConstructor')
    def generate_constructor(self, args):
        """
        Generate a constructor
        """
        buff, row = self._get_context()
        class_name = self._get_class_name()
        line = self._get_current_line()
        # Arguments are comma separated
        passed_arguments = line.strip().split(',')
        # Arguments include a type and a name separated by a space
        arguments = [Argument(*(a.strip().split(' '))) for a in passed_arguments]

        # All available constructors
        constructors = Constructor.get_all_constructors(class_name, buff,\
                                                include_noargs=True)
        # Choose one
        chained_constructor = self._prompt_constructor(constructors)
        if not chained_constructor:
            return

        # Build string
        # New arguments
        arguments_string = ", ".join([str(a) for a in arguments])
        indentation = get_indentation(line)
        # Method signature
        new_constructor_signature = '{}public {}({}'.format(indentation, class_name,
                                      arguments_string)
        # Chained constructor arguments
        constructor_arguments = Argument.parse(buff[chained_constructor.row])
        if constructor_arguments:
            if arguments:
                new_constructor_signature += ", "
            new_constructor_signature += ", ".join([str(a).strip() for a in constructor_arguments])
        new_constructor_signature +=  ") {"

        # Call chained constructor
        call_to_chained_constructor = indentation*2 + chained_constructor.text
        # Assign variables
        middle = "\n".join([indentation * 2 + "this.{0} = {0};".format(a.name)for a in arguments])
        # Close
        bottom = indentation + '}'

        # Finalize string
        new_constructor = "\n".join([new_constructor_signature, call_to_chained_constructor, middle, bottom])
        if not new_constructor:
            return

        # Remove trigger
        del buff[row-1]
        # Insert constructor
        buff.append(new_constructor.splitlines(), row-1)

    @neovim.function('ChainSuper')
    def superConstructor(self, args):
        """
        Insert call to a super constructor
        Prompt if there is more than one match.
        """
        # Context
        os.chdir(self._get_directory())
        buff, row = self._get_context()
        class_name = self._get_class_name()

        # Get super
        super_class = SuperClass(buff)
        # Get constructors
        current_constructor = Constructor.get_current_constructor(row,\
                                               class_name, buff)
        if not current_constructor:
            return;
        constructors = super_class.get_all_constructors(class_name, buff,\
                                                    include_noargs=True)
        self.return_constructors(constructors, current_constructor)


    def return_constructors(self, constructors, current_constructor):
        """
        Take a list of constructors and the current constructor
        Insert another constructor.
        Prompt if there is more than one match.
        """
        if not constructors:
            return

        constructor = self._prompt_constructor(constructors)
        result = str(constructor)
        if not result:
            return
        # Indentation
        indentation = get_indentation(self._get_current_line())
        if indentation is None:
            indentation = ''
        # Append result
        self.nvim.current.buffer.append(indentation + result, current_constructor.row+1)

    def _prompt_constructor(self, constructors):
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
        return constructors[index]

class Constructor:
    def __init__(self, class_name, line=None, row=None):
        self.class_name = class_name
        self.text = ""
        self.row = row
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
        variable_names = []

        if match:
            if match.group(1):
                arguments = match.group(1)\
                                .replace(')', '')\
                                .split(',')
                # Filter out variable names
                for argument in arguments:
                    words = argument.strip().split(" ")
                    if len(words) > 1:
                        variable_names.append(words[1])
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
                constructor = Constructor(class_name, text[row] ,row)
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

class SuperClass:
    def __init__(self, child_text):
        self.child_text = child_text
        self.class_name = self._get_class_name()
        self.path = self.class_name + ".java"
        with open(self.path) as f:
            self.text = f.readlines()

    def _get_class_name(self):
        pattern = re.compile(r"public class \w* extends (\w*)")
        for line in self.child_text:
            match = pattern.search(line)
            if match:
                return match.group(1)

    def get_all_constructors(self, class_name, text, include_noargs=True):
        result = Constructor.get_all_constructors(self.class_name, self.text)
        for r in result:
            r.text = r.text.replace('this(', 'super(')
        return result

class Argument:
    def __init__(self, type_, name):
        self.type = type_
        self.name = name

    def __str__(self):
        return "{} {}".format(self.type, self.name)

    @staticmethod
    def parse(line):
        """
        Take a line, return a list of arguments
        """
        pattern = r"public .*\(((\w+ \w+(, +|\)))*)"
        prog = re.compile(pattern)
        match = prog.search(line)
        arguments = []
        if not match:
            return
        if not match.group(1):
            return
        arguments = match.group(1)\
                         .replace(')', '')\
                         .split(',')
        for a in arguments:
            properties = a.strip(' ').split(' ')
            if len(properties) == 2:
                type_, name = properties
                a = Argument(type_.strip(), name.strip())
        return arguments

def get_indentation(line):
    """
    Take a line, and return its indentation as string
    """
    pattern = re.compile(r"(.*?)(\w|\})")
    match = pattern.search(line)
    if not match:
        return
    indentation = match.group(1)
    add_extra_indent = ('public', '}')
    if any(s in line for s in add_extra_indent):
        return indentation + indentation
    return indentation


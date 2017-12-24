import re

class_name = "Werknemer"
# pattern = r"public " + re.escape(class_name) +  r"(((\w+ \w+(, |\)))+)"
# pattern = r"public \w\((\w (\w),?)+\)"
pattern = r"public " + re.escape(class_name) + r"\(((\w+ \w+(, |\)))+)"
prog = re.compile(pattern)
line = "public Werknemer(String naam, int salaris){"
match = prog.search(line)
if match:
    arguments = match.group(1)
                    .replace(')', '')
                    .split(',')
    # Filter out variable names
    variable_names = [argument.strip().split(" ")[1] for a in arguments]
    return "this({});".format(", ".join(variable_names))

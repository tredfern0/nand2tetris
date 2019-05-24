import sys


class VM:
    def __init__(self):
        self.redirect_dict = {
            "push": self.parse_push,
            "pop": self.parse_pop,
            "add": self.parse_add,
            "sub": self.parse_sub,
            "eq": self.parse_eq,
            "lt": self.parse_lt,
            "gt": self.parse_gt,
            "neg": self.parse_neg,
            "and": self.parse_and,
            "or": self.parse_or,
            "not": self.parse_not,
        }

        self.mem_loc_funcs = {
            "constant": self._constant,
            "local": self._local,
            "this": self._this,
            "that": self._that,
            "temp": self._temp,
            "argument": self._argument,
            "static": self._static,
            "pointer": self._pointer,
        }

        """
        Standard VM mapping on the Hack platform
        0 SP - stack pointer
        1 LCL - pointer to base address of virtual segment
        2 ARG - ^
        3 THIS - ^
        4 THAT - ^
        5-12 temp segment
        13-15 general purpose registers - used for any purpose
        16-255 static variables - xyz.i symbols
                              each static variable i in file xyz.vm is translated to xyz.i
        256-2047 stack
        """
        self.start_addresses = {"LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4, "TEMP": 5}

        self.jump_index = 0

        self.filename = ""

    @staticmethod
    def comment_line(line):
        return "// {}".format(line)

    def _local(self, arg):
        mem_index = self.start_addresses["LCL"]
        ret = ["@{}".format(mem_index), "D=M", "@{}".format(arg)]
        return ret

    def _argument(self, arg):
        mem_index = self.start_addresses["ARG"]
        ret = ["@{}".format(mem_index), "D=M", "@{}".format(arg)]
        return ret

    def _this(self, arg):
        mem_index = self.start_addresses["THIS"]
        ret = ["@{}".format(mem_index), "D=M", "@{}".format(arg)]
        return ret

    def _that(self, arg):
        mem_index = self.start_addresses["THAT"]  # +int(arg)
        ret = ["@{}".format(mem_index), "D=M", "@{}".format(arg)]
        return ret

    @staticmethod
    def _constant(arg):
        ret = ["@{}".format(arg)]
        return ret

    def _static(self, arg):
        ret = ["@{}.{}".format(self.filename, arg)]
        return ret

    def _pointer(self, arg):
        if arg == "0":
            mem_index = self.start_addresses["THIS"]
        elif arg == "1":
            mem_index = self.start_addresses["THAT"]
        ret = ["@{}".format(mem_index)]
        return ret

    def _temp(self, arg):
        mem_index = self.start_addresses["TEMP"] + int(arg)
        ret = ["@{}".format(mem_index)]
        return ret

    @staticmethod
    def _push_d():
        """
        At this point we should have already set
        D=A
        Have D set to be a pointer to the memory location of the value we want to push onto the stack
        """
        ret = [
            "@SP",
            "A=M",
            "M=D",  # Actually put the value in D onto the stack
            "@SP",
            "M=M+1",  # And increment our stack pointer
        ]
        return ret

    @staticmethod
    def _pop():
        """
        Run this first - decrement stack pointer
        Then we can do A=M so when we call M, we're pointing to proper value
        """
        ret = [
            "@SP",  # @0
            "M=M-1",  # If RAM[0]=257, set it so RAM[0]=256
            "A=M",  # If RAM[256]=-4853, save that in D
            "A=M",  # Saving the actual value in A
        ]
        return ret

    def parse_push(self, line):
        """
        Possibilities
        push constant 10
        push local
        push this
        push that
        push temp
        push argument
        """
        ret = self.mem_loc_funcs[line[1]](line[2])

        if line[1] in ["local", "this", "that", "argument"]:
            ret += ["A=D+A", "D=M"]
        elif line[1] in ["temp", "static", "pointer"]:
            ret += ["D=M"]
        elif line[1] in ["constant"]:
            ret += ["D=A"]

        ret += self._push_d()
        return ret

    def parse_pop(self, line):
        # Get the value off the stack
        # Store it in D
        # Then once we have the stack pointer pointing there, we want to set
        # the local index to this value

        # Hack to handle static pops
        if line[1] == "static":
            ret = self._pop()
            ret += [
                "D=A",  # Setting D to the memory value so we can insert it
                "@{}.{}".format(self.filename, line[2]),
                "M=D",
            ]
            return ret

        ret = self.mem_loc_funcs[line[1]](line[2])

        # For others we wanted to get memory value, here we just want the pointer
        if line[1] in ["local", "this", "that", "argument"]:
            ret += ["D=D+A"]
        elif line[1] in ["temp", "pointer"]:
            ret += ["D=A"]

        ret += self._pop()

        ### SWITCH A AND D
        # D=7, A=5
        ret += [
            "D=D+A",  # - D=12
            "A=D-A",  # - A=7
            "D=D-A",  # - D=5
            # Now A is the register where we want to put our value
            "M=D",
        ]

        return ret

    def parse_add(self, line):
        ret = self._pop()
        ret += ["D=A"]
        ret += self._pop()
        ret += ["D=D+A"]
        ret += self._push_d()

        return ret

    def parse_sub(self, line):
        ret = self._pop()
        ret += ["D=A"]
        ret += self._pop()
        ret += ["D=A-D"]
        ret += self._push_d()
        return ret

    def get_jump_indexes(self):
        jump_index0, jump_index1 = self.jump_index + 1, self.jump_index + 2
        self.jump_index += 2
        return jump_index0, jump_index1

    def parse_eq(self, line):
        jump_index0, jump_index1 = self.get_jump_indexes()
        ret = self._pop()
        ret += ["D=A"]
        ret += self._pop()

        # If they're equal, D-A==0
        ret += [
            "D=D-A",
            "@MEMCONDJMP_{}".format(jump_index0),
            "D;JEQ",
            # If they're NOT equal, write a false
            "D=0",
        ]
        ret += self._push_d()
        ret += [
            "@ENDOFFUNC_{}".format(jump_index1),
            "0;JEQ",
            # If they ARE equal, write true
            "(MEMCONDJMP_{})".format(jump_index0),
            "D=-1",  # True
        ]
        ret += self._push_d()
        ret += ["(ENDOFFUNC_{})".format(jump_index1)]

        return ret

    def parse_lt(self, line):
        jump_index0, jump_index1 = self.get_jump_indexes()

        ret = self._pop()
        ret += ["D=A"]
        ret += self._pop()
        # If they're equal, D-A==0
        ret += [
            "D=A-D",
            "@MEMCONDJMP_{}".format(jump_index0),
            "D;JLT",
            # If they're NOT equal, write a false
            "D=0",
        ]
        ret += self._push_d()
        ret += [
            "@ENDOFFUNC_{}".format(jump_index1),
            "0;JEQ",
            # If they ARE equal, write true
            "(MEMCONDJMP_{})".format(jump_index0),
            "D=-1",  # True
        ]
        ret += self._push_d()
        ret += ["(ENDOFFUNC_{})".format(jump_index1)]

        return ret

    def parse_gt(self, line):
        jump_index0, jump_index1 = self.get_jump_indexes()

        ret = self._pop()
        ret += ["D=A"]
        ret += self._pop()
        # If they're equal, D-A==0
        ret += [
            "D=A-D",
            "@MEMCONDJMP_{}".format(jump_index0),
            "D;JGT",
            # If they're NOT equal, write a false
            "D=0",
        ]
        ret += self._push_d()
        ret += [
            "@ENDOFFUNC_{}".format(jump_index1),
            "0;JEQ",
            # If they ARE equal, write true
            "(MEMCONDJMP_{})".format(jump_index0),
            "D=-1",  # True
        ]
        ret += self._push_d()
        ret += ["(ENDOFFUNC_{})".format(jump_index1)]

        return ret

    def parse_neg(self, line):
        # M=-M
        ret = self._pop()
        ret += ["D=-A"]
        ret += self._push_d()
        return ret

    def parse_and(self, line):
        # D&M
        ret = self._pop()
        ret += ["D=A"]
        ret += self._pop()
        ret += ["D=D&A"]
        ret += self._push_d()
        return ret

    def parse_or(self, line):
        # D|M
        ret = self._pop()
        ret += ["D=A"]
        ret += self._pop()
        ret += ["D=D|A"]
        ret += self._push_d()
        return ret

    def parse_not(self, line):
        #!M
        ret = self._pop()
        ret += ["D=!A"]
        ret += self._push_d()
        return ret

    @staticmethod
    def clean_line(line):
        if "//" in line:
            line = line[: line.find("//")]
        return line

    @staticmethod
    def write_file(filename, f):
        with open(filename, "w") as wf:
            wf.write(f)

    def generate_tests(self):

        command = "push"
        for command in ["push", "pop"]:
            for mem_type in ["constant", "local", "this", "that", "temp", "argument"]:
                converted_lines = []
                l = "{} {} 2".format(command, mem_type)
                comment = self.comment_line(l)
                converted_lines.append(comment)
                l = l.split()
                conv = self.redirect_dict[l[0]](l)
                converted_lines += conv
                assembler_lines = "\n".join(converted_lines)
                self.write_file(
                    "{}_{}_2.asm".format(command, mem_type), assembler_lines
                )

        for cmd in ["add", "sub", "eq", "lt", "gt", "neg", "and", "or", "not"]:
            l = cmd
            converted_lines = []
            comment = self.comment_line(l)
            converted_lines.append(comment)
            l = l.split()
            conv = self.redirect_dict[l[0]](l)
            converted_lines += conv
            assembler_lines = "\n".join(converted_lines)
            self.write_file("{}.asm".format(cmd), assembler_lines)

    def run(self):
        filename = conv_file.split(".")[0]
        self.filename = filename.split("/")[-1]

        with open(conv_file, "r") as f:
            conv_file_raw = f.read()
            conv_file_raw = conv_file_raw.split("\n")

            converted_lines = []
            for line in conv_file_raw:

                l = self.clean_line(line)
                if l:
                    comment = self.comment_line(l)
                    converted_lines.append(comment)
                    l = l.split()
                    conv = self.redirect_dict[l[0]](l)
                    converted_lines += conv

            assembler_lines = "\n".join(converted_lines)
            write_filename = "{}.asm".format(conv_file[:-3])
            self.write_file(write_filename, assembler_lines)

    def run_with_input_file(self, conv_file):
        filename = conv_file.split(".")[0]
        self.filename = filename.split("/")[-1]

        with open(conv_file, "r") as f:
            conv_file_raw = f.read()
            conv_file_raw = conv_file_raw.split("\n")

            converted_lines = []
            for line in conv_file_raw:

                l = self.clean_line(line)
                if l:
                    comment = self.comment_line(l)
                    converted_lines.append(comment)
                    l = l.split()
                    conv = self.redirect_dict[l[0]](l)
                    converted_lines += conv

            assembler_lines = "\n".join(converted_lines)
            write_filename = "{}.asm".format(conv_file[:-3])
            self.write_file(write_filename, assembler_lines)


if __name__ == "__main__":
    conv_file = sys.argv[1]
    v = VM()
    v.run_with_input_file(conv_file)

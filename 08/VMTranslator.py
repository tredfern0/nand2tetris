import sys
import os


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
            "label": self.parse_label,
            "goto": self.parse_goto,
            "if-goto": self.parse_if_goto,
            "function": self.parse_function,
            "return": self.parse_return,
            "call": self.parse_call,
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
        ### Standard VM mapping on the Hack platform
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
        self.ret_index = 0
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
        mem_index = self.start_addresses["THAT"]
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
        # SP++
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
        Have D set to be a pointer to the memory location of the value
        we want to push onto the stack
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
            "@SP",  # A=0
            "M=M-1",  # If RAM[0]=257, set it so RAM[0]=256
            "A=M",  # A is still 0, so A=RAM[0], now A=257
            "A=M",  # So now we're saving the actual value from RAM[257] in A
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

    def parse_label(self, line):
        # label MAIN_LOOP_START
        ret = ["({})".format(line[1])]
        return ret

    def parse_goto(self, line):
        # goto END_PROGRAM
        ret = ["@{}".format(line[1]), "0;JMP"]
        return ret

    def parse_if_goto(self, line):
        # if-goto COMPUTE_ELEMENT
        # We want to pop the top item from the stack, and compare it to 0
        # Then do a jumpNEQ
        ret = self._pop()
        ret += ["D=A"]
        ret += ["@{}".format(line[1]), "D;JNE"]
        return ret

    def parse_function(self, line):
        # function Sys.init 0
        # function SimpleFunction.test 2
        # where 0 or 2 is the number of local arguments you need to allocate memory for

        # (functionName)  #Declare the label
        ret = ["({})".format(line[1])]
        # repeat nVars times: push 0  #For our local variables
        for _ in range(int(line[2])):
            ret += ["D=0"]
            ret += self._push_d()
        return ret

    def parse_return(self, null):
        # return
        # Always just returns the value on the top of the stack - must ALWAYS exist

        # endFrame = LCL  #So this points at the end of the frame in the host RAM
        ret = [
            "@LCL",  # A=1
            "D=M",  # D=RAM[1] ,could be 1040, whatever memory location is of LCL pointer, this is endFrame
            "@TEMP",  # A=5
            "M=D",  # in RAM[5], store the pointer value of LCL
        ]

        # retAddress = *(endFrame-5)  #Gets the return address
        # D=M  #D=RAM[5]  Don't need this because we still have D=endFrame
        ret += [
            "@5",
            "A=D-A",  # A= endFrame-5, this will be the RAM of where we stored our pointer
            "D=M",  # Now storing that pointer in D
            "@6",  # TEMP+1
            "M=D",  # RAM[6] = pointer value of LCL-5
        ]

        # *ARG = pop()  #Pop return value, put it to where our ARG pointer is
        ret += [
            "@ARG",  # A=5
            "D=M",  # D=RAM[5], so the pointer to the start location, so D=543
        ]
        ret += self._pop()  # A=value at SP, our popped value, A=-32
        # We want RAM[543]=-32, RAM[D]=A, so need to switch them
        ret += [
            "D=D+A",  # - D=12
            "A=D-A",  # - A=7
            "D=D-A",  # - D=5
            # Now A is the register where we want to put our value
            "M=D",  # Is what we want, I think this is it.
        ]

        # SP = ARG+1  #Reposition stack pointer to proper spot
        # First get D=ARG+1
        ret += ["@ARG", "D=M+1", "@SP", "M=D"]  # D=RAM[2]+1  # A=0  # RAM[0] = RAM[2]+1
        # THAT = *(endFrame-1)  #Restores THAT
        ret += [
            "@TEMP",  # A=5, where we stored endFrame
            "D=M",  # D=RAM[5], so D=endFrame, maybe 555
            "@1",  # A=1, want to subtract this from endFrame
            "A=D-A",  # A = 555-1
            "D=M",  # D=RAM[554]
            "@THAT",  # A=4, where we want to store this new pointer
            "M=D",  # RAM[4] = so RAM[4]=endFrame
        ]

        # THIS = *(endFrame-2)
        ret += [
            "@TEMP",  # A=5, where we stored endFrame
            "D=M",  # D=RAM[5], so D=endFrame
            "@2",  # A=1, want to subtract this from endFrame
            "A=D-A",  # A = 555-1
            "D=M",  # D=RAM[554]
            "@THIS",  # A=4, where we want to store this new pointer
            "M=D",  # RAM[4] = so RAM[4]=endFrame
        ]

        # ARG = *(endFrame-3)
        ret += [
            "@TEMP",  # A=5, where we stored endFrame
            "D=M",  # D=RAM[5], so D=endFrame
            "@3",  # A=1, want to subtract this from endFrame
            "A=D-A",  # A = 555-1
            "D=M",  # D=RAM[554]
            "@ARG",  # A=4, where we want to store this new pointer
            "M=D",  # RAM[4] = so RAM[4]=endFrame
        ]

        # LCL = *(endFrame-4)
        ret += [
            "@TEMP",  # A=5, where we stored endFrame
            "D=M",  # D=RAM[5], so D=endFrame
            "@4",  # A=1, want to subtract this from endFrame
            "A=D-A",  # A = 555-1
            "D=M",  # D=RAM[554]
            "@LCL",  # A=4, where we want to store this new pointer
            "M=D",  # RAM[4] = so RAM[4]=endFrame
        ]

        # goto retAddr #Jump to return address, NOT A LABEL, get the actual return address we popped
        ret += [
            "@6",  # TEMP+1 - this is where we stored the return address!
            "A=M",  # RAM[6] = actual return address of what we stored here
            "0;JMP",  # Jump to this address
        ]

        return ret

    def parse_call(self, line):
        # call Main.fibonacci 1
        # where 1 is the number of arguments you pass in.  Take the top stack values as args

        # Initialize the return address we'll use here
        return_address = "{}${}".format(line[1].split(".")[-1], self.ret_index)
        self.ret_index += 1

        # push returnAddress  #using the label below
        ret = ["@{}".format(return_address), "D=A"]
        ret += self._push_d()

        # push LCL  #save these values of the caller
        ret += ["@LCL", "D=M"]  # A=1  # D=RAM[1]
        ret += self._push_d()  # Save this pointer value to our stack

        # push ARG
        ret += ["@ARG", "D=M"]  # A=1  # D=RAM[1]
        ret += self._push_d()  # Save this pointer value to our stack

        # push THIS
        ret += ["@THIS", "D=M"]  # A=1  # D=RAM[1]
        ret += self._push_d()  # Save this pointer value to our stack

        # push THAT
        ret += ["@THAT", "D=M"]  # A=1  # D=RAM[1]
        ret += self._push_d()  # Save this pointer value to our stack

        # ARG = SP-5-nArgs  #reposition ARG
        ret += [
            "@SP",
            "D=M",  # D=RAM[0], our current stack pointer
            "@5",  # First val to subtract
            "D=D-A",  # Subtract it
            "@{}".format(line[2]),  # A=numArgs
            "D=D-A",  # Subtract those too
            "@ARG",
            "M=D",  # Set our arg pointer to this line
        ]

        # LCL = SP  #reposition LCL
        ret += [
            "@SP",  # A=0
            "D=M",  # D=RAM[0]
            "@LCL",
            "M=D",  # LCL = whatever pointer was in SP
        ]

        # goto functionName
        ret += ["@{}".format(line[1]), "0;JMP"]

        # (returnAddress)   #Declares a label for the return address
        ret += ["({})".format(return_address)]

        return ret

    def write_init(self):
        """
        Generate initialization code that needs to go at the top of each asm file

        Only need to do this if we have multiple files, if it's a directory
        """
        # SP=256
        ret = ["@256", "D=A", "@SP", "M=D"]
        # Call Sys.init
        ret += self.parse_call(["call", "Sys.init", "0"])
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
                # Can't pop
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

    def get_converted_lines(self, conv_file):
        with open(conv_file, "r") as f:
            conv_file_raw = f.read()
            conv_file_raw = conv_file_raw.split("\n")

            converted_lines = []
            for line in conv_file_raw:

                l = self.clean_line(line)
                if l:
                    comment = self.comment_line(l)
                    converted_lines.append(comment)
                    if l != "return":
                        l = l.split()
                        conv = self.redirect_dict[l[0]](l)
                    else:
                        conv = self.redirect_dict[l](l)
                    converted_lines += conv
        return converted_lines

    def run_with_input_file(self, conv_dir_or_file):
        # It's a file
        if not os.path.isdir(conv_dir_or_file):
            conv_file = conv_dir_or_file

            filename = conv_file.split(".")[0]
            self.filename = filename.split("/")[-1]

            converted_lines = self.get_converted_lines(conv_file)

            assembler_lines = "\n".join(converted_lines)
            write_filename = "{}.asm".format(conv_file[:-3])
            self.write_file(write_filename, assembler_lines)

        else:
            # It's a directory, we want - the folder name (for our output.asm file)
            # Iterate over the files, starting with Main

            # Get the full write filename
            last_folder = conv_dir_or_file.split(os.sep)[-1]
            write_filename = "{}.asm".format(last_folder)
            write_filename = os.path.join(conv_dir_or_file, write_filename)

            # Need this for all directories
            converted_lines = self.write_init()
            for filename in os.listdir(conv_dir_or_file):
                if filename.endswith(".vm"):
                    # For our static files
                    self.filename = filename
                    converted_lines += self.get_converted_lines(
                        os.path.join(conv_dir_or_file, filename)
                    )
            assembler_lines = "\n".join(converted_lines)
            self.write_file(write_filename, assembler_lines)


if __name__ == "__main__":
    # conv_file = "MemoryAccess/BasicTest/BasicTest.vm"
    # conv_file = "MemoryAccess/PointerTest/PointerTest.vm"
    # conv_file = "MemoryAccess/StaticTest/StaticTest.vm"
    # conv_file = "StackArithmetic/SimpleAdd/SimpleAdd.vm"
    # conv_file = "StackArithmetic/StackTest/StackTest.vm"
    conv_file = sys.argv[1]
    v = VM()
    v.run_with_input_file(conv_file)

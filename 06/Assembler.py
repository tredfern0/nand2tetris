class Parser:
    def __init__(self):
        self.current_n = 16

        self.table = {
            "R0": 0,
            "R1": 1,
            "R2": 2,
            "R3": 3,
            "R4": 4,
            "R5": 5,
            "R6": 6,
            "R7": 7,
            "R8": 8,
            "R9": 9,
            "R10": 10,
            "R11": 11,
            "R12": 12,
            "R13": 13,
            "R14": 14,
            "R15": 15,
            "SCREEN": 16384,
            "KBD": 24576,
            "SP": 0,
            "LCL": 1,
            "ARG": 2,
            "THIS": 3,
            "THAT": 4,
        }

        # C-instruction have three parts-
        # dest, comp, jump.  All optional?
        self.comp = {
            "0": "0101010",
            "1": "0111111",
            "-1": "0111010",
            "D": "0001100",
            "A": "0110000",
            "!D": "0001101",
            "!A": "0110001",
            "-D": "0001111",
            "-A": "0110011",
            "D+1": "0011111",
            "A+1": "0110111",
            "D-1": "0001110",
            "A-1": "0110010",
            "D+A": "0000010",
            "D-A": "0010011",
            "A-D": "0000111",
            "D&A": "0000000",
            "D|A": "0010101",
            "M": "1110000",
            "!M": "1110001",
            "-M": "1110011",
            "M+1": "1110111",
            "M-1": "1110010",
            "D+M": "1000010",
            "D-M": "1010011",
            "M-D": "1000111",
            "D&M": "1000000",
            "D|M": "1010101",
        }

        self.dest = {
            "null": "000",
            "M": "001",
            "D": "010",
            "MD": "011",
            "A": "100",
            "AM": "101",
            "AD": "110",
            "AMD": "111",
        }

        self.jump = {
            "null": "000",
            "JGT": "001",
            "JEQ": "010",
            "JGE": "011",
            "JLT": "100",
            "JNE": "101",
            "JLE": "110",
            "JMP": "111",
        }

    @staticmethod
    def _to_binary(num):
        """
        Returns a string representing number in binary
        """
        return bin(num)[2:]

    @staticmethod
    def _clean_line(l):
        """
        Remove all white space, remove all comments
        """
        # Remove comments -
        try:
            l = l[: l.index("//")]
        except:
            pass
        # Remove spaces
        l = l.replace(" ", "")
        return l

    @staticmethod
    def _jump_check(l):
        """
        Return jump instruction if its in parentheses
        """
        if "(" in l and ")" in l:
            return l.replace("(", "").replace(")", "")
        return None

    def _a_instruction_check(self, l):
        """
        Return a instruction which can either be @ number, or @ variable
        """

        def a_variable_conv(str_inst):
            if str_inst in self.table:
                raw_numb = self.table[str_inst]
            else:
                # If it's not in the table, we need to start at 16 and increment
                raw_numb = self.current_n
                self.table[str_inst] = raw_numb

                self.current_n += 1

            return raw_numb

        if "@" in l:
            inst = l.replace("@", "")
            try:
                inst_val = int(inst)
            except:
                inst_val = a_variable_conv(inst)
            # return inst_val
            ret_inst = self._to_binary(int(inst_val))
            ret_val = "0" * (16 - len(ret_inst))
            ret_val = ret_val + ret_inst
            return ret_val

        return None

    def _c_instruction_check(self, l):
        # dest=comp;jump
        # possibilities -
        # D=D-M
        # 0;JMP
        def get_dest_val(l, equal_loc):
            if equal_loc:
                dest_val = l[:equal_loc]
            else:
                dest_val = "null"
            return dest_val

        def get_comp_val(l, equal_loc, semicolon_loc):
            if equal_loc and semicolon_loc:
                comp_val = l[equal_loc + 1 : semicolon_loc]
            elif equal_loc:
                comp_val = l[equal_loc + 1 :]
            elif semicolon_loc:
                comp_val = l[:semicolon_loc]
            return comp_val

        def get_jump_val(l, semicolon_loc):
            if semicolon_loc:
                jump_val = l[semicolon_loc + 1 :]
            else:
                jump_val = "null"
            return jump_val

        if "=" in l or ";" in l:
            try:
                equal_index = l.index("=")
            except:
                equal_index = 0
            try:
                semicolon_index = l.index(";")
            except:
                semicolon_index = 0
            dest_ = get_dest_val(l, equal_index)
            comp_ = get_comp_val(l, equal_index, semicolon_index)
            jump_ = get_jump_val(l, semicolon_index)

            d = self.dest[dest_]
            c = self.comp[comp_]
            j = self.jump[jump_]

            full_str = "111{}{}{}".format(c, d, j)
            return full_str
        return None

    def first_pass(self, file_raw):
        """
        Build symbol table, read through and generate all addresses)
        with the () - need the line numbers
        """
        lineI = 0
        for l in file_raw:
            clean_l = self._clean_line(l)
            if clean_l:
                jump_val = self._jump_check(clean_l)
                if jump_val:
                    self.table[jump_val] = lineI
                else:
                    lineI += 1

    def second_pass(self, file_raw):
        """
        Symbol table is built, parse line
        """
        converted = []
        for l in file_raw:
            clean_l = self._clean_line(l)
            if clean_l:
                # If jump instruction, we want to keep going
                jc = self._jump_check(clean_l)
                if jc:
                    continue

                # If not a jump instruction, it's either a or c instruction
                conv = self._a_instruction_check(clean_l)
                if not conv:
                    conv = self._c_instruction_check(clean_l)

                converted.append(conv)

        converted = "\n".join(converted)
        return converted

    @staticmethod
    def write_file(filename, f):
        with open(filename, "w") as wf:
            wf.write(f)

    def test_funcs(self, file_raw):
        for l in file_raw:
            clean_l = self._clean_line(l)
            print("CLEANLINE --- ", clean_l, "--- OLD", l)
            jum = self._jump_check(clean_l)
            print("JUMP - ", jum, "GOT_FROM:", clean_l)
            ains = self._a_instruction_check(clean_l)
            print("AINSTRU - ", ains, "GOT_FROM:", clean_l)
            cins = self._c_instruction_check(clean_l)
            print("CINSTRU - ", cins, "GOT_FROM:", clean_l)


if __name__ == "__main__":
    # Testing
    # conv_file = "max/Max.asm"
    # p.test_funcs(conv_file_raw)

    for conv_file in ["max/Max.asm", "add/Add.asm", "pong/Pong.asm", "rect/Rect.asm"]:
        with open(conv_file, "r") as f:
            conv_file_raw = f.read()
            conv_file_raw = conv_file_raw.split("\n")
            p = Parser()

            # Real processing
            p.first_pass(conv_file_raw)
            machine_code = p.second_pass(conv_file_raw)

            write_filename = "{}hack".format(conv_file[:-3])
            p.write_file(write_filename, machine_code)

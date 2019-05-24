import os
import sys


class JackTokenizer:
    def __init__(self, input_file):
        """
        Opens the .jack file and gets ready to tokenize it
        """
        with open(input_file) as f:
            text = f.read()

        self.tokens = self.cleanText(text)
        self.i = 0

    def hasMoreTokens(self):
        """
        Returns bool - are there more tokens in the input?
        """
        return self.i + 1 < len(self.tokens)

    def advance(self):
        """
        Gets the next token from the input, and makes it the current token
        This method should be called only if hasMoreTokens is true
        Initially there is no current token
        """
        self.i += 1

    def firstPass(self, text):
        """
        Remove comments and leading/trailing whitespace
        """
        t = text.split("\n")
        clean_t = []

        long_comment = False

        for lInd, line in enumerate(t):
            # Want to remove comments and white space
            # Want to split up l into individual tokens
            if not line:
                continue

            # First thing is checking for end to a long comment
            if long_comment:
                if "*/" in line:
                    line = line[line.find("*/") + 2 :]
                    long_comment = False
                else:
                    continue
            # First thing is removing longer comments
            if "/*" in line and "*/" in line:
                line = "{} {}".format(
                    line[: line.find("/*")], line[line.find("*/") + 2 :]
                )
            elif "/*" in line:
                line = line[: line.find("/*")]
                long_comment = True

            if "//" in line:
                line = line[: line.find("//")]
            # Get rid of leading and trailing whitespace
            line = line.strip()
            if line:
                clean_t.append(line)

        return clean_t

    def secondPass(self, text):
        """
        From a cleaned data source, pull out tokens
        """
        token_list = []
        for lInd, l in enumerate(text):
            string_constant = False
            current_token = []
            for c in l:
                if (
                    c
                    in [
                        "{",
                        "}",
                        "(",
                        ")",
                        "[",
                        "]",
                        ".",
                        ",",
                        ";",
                        "+",
                        "-",
                        "*",
                        "/",
                        "&",
                        "|",
                        "<",
                        ">",
                        "=",
                        "~",
                    ]
                    and not string_constant
                ):
                    if current_token:
                        # Append the previous token, it's completed, and append this token
                        token_list.append("".join(current_token))
                        current_token = []
                    token_list.append(c)

                elif c == '"' and not string_constant:
                    string_constant = True
                    current_token.append("__STRINGCONST__")

                # Ending string constant - append whatever we have
                elif c == '"' and string_constant:
                    token_list.append("".join(current_token))
                    current_token = []
                    string_constant = False

                # If we have a space and not a string constant, it's a delimiter
                elif c == " " and current_token and not string_constant:
                    token_list.append("".join(current_token))
                    current_token = []

                # Handle double spaces - if we just added a token and found another space, ignore it
                elif c == " " and not current_token:
                    pass

                # This will handle spaces if are in a string constant (as we WILL have a current_token)
                # and also all other characters
                else:
                    current_token.append(c)

            # When we reach the end of the line, if we have a current_token in progress we will need to append it
            if current_token:
                token_list.append("".join(current_token))

        return token_list

    def thirdPass(self, tokens):
        """
        Precompute the type and value for each token
        """
        token_tuples = []

        for t in tokens:
            tType = self.tokenType(t.upper())
            if tType == "STRING_CONST":
                t = t.replace("__STRINGCONST__", "")
            token_tuples.append((t, tType))

        return token_tuples

    def cleanText(self, text):
        """
        Own function - try to pull all individual tokens out of text, and clean it up
        """
        # First pass - remove comments and whitespace
        lines = self.firstPass(text)

        tokens = self.secondPass(lines)

        token_tuples = self.thirdPass(tokens)

        return token_tuples

    def tokenType(self, token):
        """
        Retrns the type of the current token, as a constant
        """
        if token in [
            "CLASS",
            "METHOD",
            "FUNCTION",
            "CONSTRUCTOR",
            "INT",
            "BOOLEAN",
            "CHAR",
            "VOID",
            "VAR",
            "STATIC",
            "FIELD",
            "LET",
            "DO",
            "IF",
            "ELSE",
            "WHILE",
            "RETURN",
            "TRUE",
            "FALSE",
            "NULL",
            "THIS",
        ]:
            return "KEYWORD"

        if token in [
            "{",
            "}",
            "(",
            ")",
            "[",
            "]",
            ".",
            ",",
            ";",
            "+",
            "-",
            "*",
            "/",
            "&",
            "|",
            "<",
            ">",
            "=",
            "~",
        ]:

            return "SYMBOL"

        if "__STRINGCONST__" in token:
            return "STRING_CONST"

        if token[0] not in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            return "IDENTIFIER"

        # Only option left is integer
        return "INT_CONST"


class CompilationEngine:
    def __init__(self, jack_tokenizer_instance):
        self.jt = jack_tokenizer_instance

        # These are the terminal elements
        # "KEYWORD" (do while if)
        # "SYMBOL" (+ - ; , etc)
        # "STRING_CONST" (a string)
        # "IDENTIFIER" (_varName)
        # "INT_CONST"

        self.xml = []

        # < > " & outputed as:
        # &lt; &gt; &quot; &amp;

    def compile(self):
        """
        Starter function
        """
        while self.jt.hasMoreTokens():
            token = self.jt.tokens[self.jt.i]
            if token[0] == "class":
                self.compileClass()
            else:
                raise Exception("INVALID STARTING TOKEN")

    def _eat(self, check_dict):
        if not self._check_fields(check_dict):
            token = self.jt.tokens[self.jt.i]
            raise Exception("FAILED TO EAT VAR")
        else:
            token = self.jt.tokens[self.jt.i]

            # < > " & outputed as:
            # &lt; &gt; &quot; &amp;
            val_write = (
                token[0]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            type_write = (
                token[1]
                .lower()
                .replace("int_const", "integerConstant")
                .replace("string_const", "stringConstant")
            )
            self.xml.append("<{}>{}</{}>".format(type_write, val_write, type_write))
            self.jt.advance()

    def _check_fields(self, check_dict):
        token = self.jt.tokens[self.jt.i]
        if not any(
            token[0 if key == "token" else 1] in check_dict[key] for key in check_dict
        ):
            return False
        return True

    def _getOpenTag(self, string):
        self.xml.append("<{}>".format(string))

    def _getCloseTag(self, string):
        self.xml.append("</{}>".format(string))

    def compileClass(self):
        """
        Compiles a complete class

        class className { classVarDec* subroutineDec* }
        """
        self._getOpenTag("class")

        self._eat({"token": ["class"]})
        self._eat({"terminal": ["IDENTIFIER"]})
        self._eat({"token": ["{"]})

        while self._check_compileClassVarDec():
            self.compileClassVarDec()

        while self._check_compileSubroutineDec():
            self.compileSubroutineDec()

        self._eat({"token": ["}"]})
        self._getCloseTag("class")

    def _check_compileClassVarDec(self):
        check_dict = {"token": ["static", "field"]}
        return self._check_fields(check_dict)

    def compileClassVarDec(self):
        """
        Compiles a static variable declaration, or a field declaration
        """
        self._getOpenTag("classVarDec")
        self._eat({"token": ["static", "field"]})

        # This is MANDATORY
        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        self._eat({"terminal": ["IDENTIFIER"]})

        # Optional (, varName)
        while self._check_fields({"token": [","]}):
            self._eat({"token": [","]})
            self._eat({"terminal": ["IDENTIFIER"]})

        self._eat({"token": [";"]})

        self._getCloseTag("classVarDec")

    def _check_compileSubroutineDec(self):

        check_dict = {"token": ["constructor", "function", "method"]}
        return self._check_fields(check_dict)

    def compileSubroutineDec(self):
        """
        Compiles a complete method, function, or constructor
        """
        self._getOpenTag("subroutineDec")
        self._eat({"token": ["constructor", "function", "method"]})

        # TYPE (or void)
        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        # subroutineName
        self._eat({"terminal": ["IDENTIFIER"]})

        self._eat({"token": ["("]})

        self.compileParameterList()

        self._eat({"token": [")"]})

        self.compileSubroutineBody()

        self._getCloseTag("subroutineDec")

    def _check_compileParameterList(self):
        check_dict = {"terminal": ["KEYWORD", "IDENTIFIER"]}
        return self._check_fields(check_dict)

    def compileParameterList(self):
        """
        Compiles a (possibly empty) parameter list.  Does not handle the enclosing ()
        """
        self._getOpenTag("parameterList")

        # type varName
        if self._check_fields({"terminal": ["KEYWORD", "IDENTIFIER"]}):
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        while self._check_fields({"token": [","]}):
            self._eat({"token": [","]})
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        self._getCloseTag("parameterList")

    def compileSubroutineBody(self):
        """
        Compiles a subroutine's body
        """
        self._getOpenTag("subroutineBody")
        self._eat({"token": ["{"]})

        while self._check_compileVarDec():
            self.compileVarDec()

        self.compileStatements()

        self._eat({"token": ["}"]})

        self._getCloseTag("subroutineBody")

    def _check_compileVarDec(self):
        return self._check_fields({"token": ["var"]})

    def compileVarDec(self):
        """
        Compiles a var declaration
        """
        self._getOpenTag("varDec")
        self._eat({"token": ["var"]})

        # TYPE
        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})
        # VARNAME
        self._eat({"terminal": ["IDENTIFIER"]})

        while self._check_fields({"token": [","]}):
            self._eat({"token": [","]})
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        self._eat({"token": [";"]})

        self._getCloseTag("varDec")

    def compileStatements(self):
        """
        Compiles a sequence of statements.  Does not handle the enclosing {}
        """
        self._getOpenTag("statements")

        while self._check_fields({"token": ["let", "if", "while", "do", "return"]}):
            self._compileStatement()

        self._getCloseTag("statements")

    def _compileStatement(self):
        token = self.jt.tokens[self.jt.i]
        if token[0] == "let":
            self.compileLet()
        elif token[0] == "if":
            self.compileIf()
        elif token[0] == "while":
            self.compileWhile()
        elif token[0] == "do":
            self.compileDo()
        elif token[0] == "return":
            self.compileReturn()

    def compileLet(self):
        """
        Compiles a let statement
        """
        self._getOpenTag("letStatement")
        self._eat({"token": ["let"]})
        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        if self._check_fields({"token": ["["]}):
            self._eat({"token": ["["]})
            self.compileExpression()
            self._eat({"token": ["]"]})

        self._eat({"token": ["="]})
        self.compileExpression()

        self._eat({"token": [";"]})

        self._getCloseTag("letStatement")

    def compileIf(self):
        """
        Compiles an if statement, possibly with a trailing else clause
        """
        self._getOpenTag("ifStatement")
        self._eat({"token": ["if"]})

        self._eat({"token": ["("]})
        self.compileExpression()
        self._eat({"token": [")"]})

        self._eat({"token": ["{"]})
        self.compileStatements()
        self._eat({"token": ["}"]})

        if self._check_fields({"token": ["else"]}):
            self._eat({"token": ["else"]})
            self._eat({"token": ["{"]})
            self.compileStatements()
            self._eat({"token": ["}"]})

        self._getCloseTag("ifStatement")

    def compileWhile(self):
        """
        Compiles a while statement
        while ( expression ) { statements }
        """
        self._getOpenTag("whileStatement")
        self._eat({"token": ["while"]})

        self._eat({"token": ["("]})
        self.compileExpression()
        self._eat({"token": [")"]})

        self._eat({"token": ["{"]})
        self.compileStatements()
        self._eat({"token": ["}"]})

        self._getCloseTag("whileStatement")

    def compileDo(self):
        """
        Compiles a do statement
        """
        self._getOpenTag("doStatement")
        self._eat({"token": ["do"]})

        self._subroutineCall()

        self._eat({"token": [";"]})
        self._getCloseTag("doStatement")

    def compileReturn(self):
        """
        Compiles a return statement
        """
        self._getOpenTag("returnStatement")
        self._eat({"token": ["return"]})

        if self._check_compileExpression():
            self.compileExpression()

        self._eat({"token": [";"]})
        self._getCloseTag("returnStatement")

    def _subroutineCall(self):
        # subroutineName ( expressionList )
        # (className | varName) . subroutineName ( expressionList )
        # game.dispose();
        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        if self._check_fields({"token": ["("]}):
            self._eat({"token": ["("]})
            self.compileExpressionList()
            self._eat({"token": [")"]})
        else:
            self._eat({"token": ["."]})
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})
            self._eat({"token": ["("]})
            self.compileExpressionList()
            self._eat({"token": [")"]})

    def _check_compileOp(self):
        return self._check_fields(
            {"token": ["+", "-", "*", "/", "&", "|", "<", ">", "="]}
        )

    def _compileOp(self):
        self._eat({"terminal": ["SYMBOL"]})

    def _check_compileExpression(self):
        return self._check_compileTerm()

    def compileExpression(self):
        """
        Compiles an expression
        """
        self._getOpenTag("expression")
        self.compileTerm()

        while self._check_compileOp():
            self._compileOp()
            self.compileTerm()

        self._getCloseTag("expression")

    def _check_compileTerm(self):
        token = self.jt.tokens[self.jt.i]
        token_next = self.jt.tokens[self.jt.i + 1]

        if token[0] == "(":
            return True
        # unaryOp term
        if token[0] in ["-", "~"]:
            return True
        # subroutine
        if token_next[0] in ["(", "."]:
            return True

        # varName [ expression ]
        if token_next[0] in ["["]:
            return True
        if self._check_fields(
            {"terminal": ["KEYWORD", "IDENTIFIER", "STRING_CONST", "INT_CONST"]}
        ):
            return True

        return False

    def compileTerm(self):
        """
        Compiles a term.  If the current token is an identifier, the routine must
        distinguish between a variable, an array entry, or a subroutine call.  A single
        look-ahead token, which may be one of
        {, (, .
        should suffice to distinguish between the possibilities.  Any other
        tokne is not part of this term and should not be advanced over.

        integerConstant
        stringConstant
        keywordConstant
        varName

        varName [ expression ]
        subroutineCall        keyword (...)
        ( expression )
        unaryOp term
        """
        self._getOpenTag("term")

        token = self.jt.tokens[self.jt.i]
        token_next = self.jt.tokens[self.jt.i + 1]

        # ( expression )
        if token[0] == "(":
            self._eat({"token": ["("]})
            self.compileExpression()
            self._eat({"token": [")"]})
        # unaryOp term
        elif token[0] in ["-", "~"]:
            self._eat({"token": ["-", "~"]})
            self.compileTerm()
        # subroutine
        elif token_next[0] in ["(", "."]:
            self._subroutineCall()

        # varName [ expression ]
        elif token_next[0] in ["["]:
            self._eat({"terminal": ["IDENTIFIER"]})
            self._eat({"token": ["["]})
            self.compileExpression()
            self._eat({"token": ["]"]})

        else:
            self._eat(
                {"terminal": ["KEYWORD", "IDENTIFIER", "STRING_CONST", "INT_CONST"]}
            )

        self._getCloseTag("term")

    def compileExpressionList(self):
        """
        Compiles a (possibly empty) comma-separated
        list of expressions
        """
        self._getOpenTag("expressionList")
        if self._check_compileExpression():
            self.compileExpression()

        while self._check_fields({"token": [","]}):
            self._eat({"token": [","]})
            self.compileExpression()

        self._getCloseTag("expressionList")


class JackAnalyzer:
    def __init__(self, file_or_directory):
        # For each file
        # Create a JackTokenizer from filename.jack
        # Create an output file filename.xml, and prepare for writing

        # Use compilation engine to compile the input
        # JackTokenizer into the output file

        # Single file
        if not os.path.isdir(file_or_directory):
            jt = JackTokenizer(file_or_directory)

            ce = CompilationEngine(jt)
            ce.compile()

            xml_lines = "\n".join(ce.xml)
            write_filename = "{}.xml".format(file_or_directory[:-5])
            self.write_file(write_filename, xml_lines)

        # Directory
        else:
            for filename in os.listdir(file_or_directory):
                if filename.endswith(".jack"):
                    open_file = os.path.join(file_or_directory, filename)
                    jt = JackTokenizer(open_file)

                    ce = CompilationEngine(jt)
                    ce.compile()

                    xml_lines = "\n".join(ce.xml)
                    write_filename = "{}.xml".format(open_file[:-5])
                    self.write_file(write_filename, xml_lines)

    @staticmethod
    def write_file(filename, f):
        with open(filename, "w") as wf:
            wf.write(f)


if __name__ == "__main__":
    conv_file = sys.argv[1]
    ja = JackAnalyzer(conv_file)

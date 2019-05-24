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

        self.vm = VMWriter()

        # < > " & outputed as:
        # &lt; &gt; &quot; &amp;

        self.symbolTableClass = None
        self.symbolTableSubroutine = None

        self.current_loc = None  # class, subroutine
        self.current_kind = None  # field, static, local, argument
        self.current_type = None  # int, char, boolean, className

        self.class_name = None
        self.subroutine_name = None

        self.method_bool = False

        self.label_counts = {"IF": 0, "WHILE": 0}

        self.curr_exp = []
        self.exp_print = False

    def compile(self):
        """
        Starter function
        """
        self.symbolTableClass = SymbolTable()
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

            if self.exp_print:
                self.curr_exp.append(val_write)
            if self.curr_exp and not self.exp_print:
                self.curr_exp = []

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
        # return "<{}>".format(string)
        self.xml.append("<{}>".format(string))

    def _getCloseTag(self, string):
        # return "</{}>".format(string)
        self.xml.append("</{}>".format(string))

    def _setClassName(self):
        token = self.jt.tokens[self.jt.i]
        self.class_name = token[0]

    def _setSubroutineName(self):
        token = self.jt.tokens[self.jt.i]
        self.subroutine_name = token[0]

    def compileClass(self):
        """
        Compiles a complete class
        class className { classVarDec* subroutineDec* }
        """
        self._getOpenTag("class")

        self._eat({"token": ["class"]})
        # First identifier is the class name
        self._setClassName()
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

    def _setVarKind(self):
        token = self.jt.tokens[self.jt.i]
        self.current_kind = token[0]

    def _setVarType(self):
        token = self.jt.tokens[self.jt.i]
        self.current_type = token[0]

    def _insertToTable(self):
        token = self.jt.tokens[self.jt.i]
        varName = token[0]
        if self.current_loc == "class":
            self.symbolTableClass.insert(varName, self.current_kind, self.current_type)
        elif self.current_loc == "subroutine":
            self.symbolTableSubroutine.insert(
                varName, self.current_kind, self.current_type
            )

    def compileClassVarDec(self):
        """
        Compiles a static variable declaration, or a field declaration
        """

        self.current_loc = "class"

        self._getOpenTag("classVarDec")

        self._setVarKind()
        self._eat({"token": ["static", "field"]})

        # This is MANDATORY
        # TYPE
        self._setVarType()
        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        self._insertToTable()
        self._eat({"terminal": ["IDENTIFIER"]})

        # Optional (, varName)
        while self._check_fields({"token": [","]}):
            self._eat({"token": [","]})
            self._insertToTable()
            self._eat({"terminal": ["IDENTIFIER"]})

        self._eat({"token": [";"]})

        self._getCloseTag("classVarDec")

        self.current_loc = None

    def _check_compileSubroutineDec(self):
        check_dict = {"token": ["constructor", "function", "method"]}
        return self._check_fields(check_dict)

    def _methodCheck(self):
        """
        If subroutine is a method, set flag to true so we can pass class in as first argument
        """
        token = self.jt.tokens[self.jt.i]
        if token[0] == "method":
            self.method_bool = True

    def setFunctionInfo(self, funcKind, funcType, funcName):
        self.funcKind = funcKind
        self.funcType = funcType
        self.funcName = funcName

    def insertFunctionDeclaration(self, funcName, numArgs):
        """
        Need to allocate memory for constructors
        """
        self.vm.writeFunction(funcName, numArgs)

        if self.funcKind == "constructor":
            alloc = self.symbolTableClass.kind_counts["field"]
            self.vm.writePush("constant", alloc)
            self.vm.writeCall("Memory.alloc", 1)
            self.vm.writePop("pointer", 0)

    def compileSubroutineDec(self):
        """
        Compiles a complete method, function, or constructor
        """
        self.symbolTableSubroutine = SymbolTable()
        self._getOpenTag("subroutineDec")
        self._methodCheck()

        funcKind = self.jt.tokens[self.jt.i][0]
        self._eat({"token": ["constructor", "function", "method"]})

        # TYPE (or void)
        funcType = self.jt.tokens[self.jt.i][0]
        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        # subroutineName
        self._setSubroutineName()

        funcName = self.jt.tokens[self.jt.i][0]
        self._eat({"terminal": ["IDENTIFIER"]})

        self.setFunctionInfo(funcKind, funcType, funcName)

        self._eat({"token": ["("]})

        self.compileParameterList()

        self.method_bool = False

        self._eat({"token": [")"]})

        self.compileSubroutineBody()

        self._getCloseTag("subroutineDec")

        self.symbolTableSubroutine = None

    def _check_compileParameterList(self):
        check_dict = {"terminal": ["KEYWORD", "IDENTIFIER"]}
        return self._check_fields(check_dict)

    def compileParameterList(self):
        """
        Compiles a (possibly empty) parameter list.  Does not handle the enclosing ()
        """
        self.current_place = "PARAMETER_LIST"
        self._getOpenTag("parameterList")

        self.current_loc = "subroutine"
        self.current_kind = "argument"

        # Need to pass in class as first argument if it's a method
        if self.method_bool:
            type_ = self.class_name
            self.symbolTableSubroutine.insert("this", self.current_kind, type_)

        # type varName
        if self._check_fields({"terminal": ["KEYWORD", "IDENTIFIER"]}):
            self._setVarType()
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})
            self._insertToTable()
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        while self._check_fields({"token": [","]}):
            self._eat({"token": [","]})
            self._setVarType()
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})
            self._insertToTable()
            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        self._getCloseTag("parameterList")
        self.current_loc = None

    def compileSubroutineBody(self):
        """
        Compiles a subroutine's body
        """
        self._getOpenTag("subroutineBody")
        self._eat({"token": ["{"]})

        self.totVars = 0
        while self._check_compileVarDec():
            self.compileVarDec()

        self.insertFunctionDeclaration(
            "{}.{}".format(self.class_name, self.funcName), self.totVars
        )

        if self.funcKind == "method":
            # If it's a method, we need to push argument 0 and pop pointer 0
            self.vm.writePush("argument", 0)
            self.vm.writePop("pointer", 0)

        self.compileStatements()

        self._eat({"token": ["}"]})

        self._getCloseTag("subroutineBody")

    def _check_compileVarDec(self):
        return self._check_fields({"token": ["var"]})

    def compileVarDec(self):
        """
        Compiles a var declaration
        """
        self.current_loc = "subroutine"

        self._getOpenTag("varDec")

        self._setVarKind()
        self._eat({"token": ["var"]})

        # TYPE
        self._setVarType()
        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})
        # VARNAME
        self._insertToTable()

        self._eat({"terminal": ["IDENTIFIER"]})

        # Need to keep track of number of local vars
        self.totVars += 1

        while self._check_fields({"token": [","]}):
            self.totVars += 1
            self._eat({"token": [","]})
            self._insertToTable()

            self._eat({"terminal": ["IDENTIFIER"]})

        self._eat({"token": [";"]})

        self._getCloseTag("varDec")

        self.current_loc = None

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

        varName = self.jt.tokens[self.jt.i][0]
        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        arrayBool = False
        if self._check_fields({"token": ["["]}):
            arrayBool = True

            self._eat({"token": ["["]})
            self.compileExpression()
            self._eat({"token": ["]"]})

        self._eat({"token": ["="]})

        # If it's an array we need to add these two
        if arrayBool:
            self._pushHandler(varName)
            self.vm.writeArithmetic("add")

        self.exp_print = True

        self.compileExpression()

        if arrayBool:
            self.vm.writePop("temp", 0)
            self.vm.writePop("pointer", 1)
            self.vm.writePush("temp", 0)
            self.vm.writePop("that", 0)
        else:
            self._popHandler(varName)

        self.exp_print = False
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

        true_lbl = "IF_TRUE{}".format(self.label_counts["IF"])
        false_lbl = "IF_FALSE{}".format(self.label_counts["IF"])
        end_lbl = "IF_END{}".format(self.label_counts["IF"])
        self.label_counts["IF"] += 1

        # if true go to true label
        # jump to false label
        # true label
        self.vm.writeIf(true_lbl)
        self.vm.writeGoto(false_lbl)
        self.vm.writeLabel(true_lbl)

        self._eat({"token": ["{"]})
        self.compileStatements()
        self._eat({"token": ["}"]})

        # jump to end
        self.vm.writeGoto(end_lbl)

        # false label
        self.vm.writeLabel(false_lbl)

        if self._check_fields({"token": ["else"]}):
            self._eat({"token": ["else"]})
            self._eat({"token": ["{"]})
            self.compileStatements()
            self._eat({"token": ["}"]})

        # end label
        self.vm.writeLabel(end_lbl)

        self._getCloseTag("ifStatement")

    def compileWhile(self):
        """
        Compiles a while statement
        while ( expression ) { statements }
        """
        self._getOpenTag("whileStatement")
        self._eat({"token": ["while"]})

        random_lbl1 = "WHILE_LBL_{}".format(self.label_counts["WHILE"])
        self.label_counts["WHILE"] += 1
        random_lbl2 = "WHILE_LBL_{}".format(self.label_counts["WHILE"])
        self.label_counts["WHILE"] += 1

        self.vm.writeLabel(random_lbl1)

        self._eat({"token": ["("]})
        self.compileExpression()
        self._eat({"token": [")"]})

        self.vm.writeArithmetic("not")
        self.vm.writeIf(random_lbl2)

        self._eat({"token": ["{"]})
        self.compileStatements()
        self._eat({"token": ["}"]})

        self.vm.writeGoto(random_lbl1)

        self.vm.writeLabel(random_lbl2)

        self._getCloseTag("whileStatement")

    def compileDo(self):
        """
        Compiles a do statement
        """
        self._getOpenTag("doStatement")
        self._eat({"token": ["do"]})

        self._subroutineCall(True)

        # We have to pop to temp 0?
        self.vm.writePop("temp", 0)

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

        # If it's void we need to push constant 0 and return
        if self.funcType.upper() == "VOID":
            self.vm.writePush("constant", 0)
        # If it's a constructor, will always return this
        if self.funcKind.upper() == "CONSTRUCTOR":
            self.vm.writePush("pointer", 0)
        self.vm.writeReturn()

        self._eat({"token": [";"]})
        self._getCloseTag("returnStatement")

    def _subroutineCall(self, doCall=False):
        # subroutineName ( expressionList )
        # (className | varName) . subroutineName ( expressionList )
        funcName = self.jt.tokens[self.jt.i][0]

        self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})

        if self._check_fields({"token": ["("]}):

            self._eat({"token": ["("]})
            expCount = self.compileExpressionList()
            self._eat({"token": [")"]})

            funcName = "{}.{}".format(self.class_name, funcName)
            self.vm.writePush("pointer", 0)
            self.vm.writeCall(funcName, expCount)

        else:
            self._eat({"token": ["."]})

            bonusArgs = 0

            try:
                className = self.symbolTableSubroutine.table[funcName]["type"]
                localLoc = self.symbolTableSubroutine.table[funcName]["number"]
                bonusArgs = 1
            except:
                className = funcName
            funcName = "{}.{}".format(className, self.jt.tokens[self.jt.i][0])

            self._eat({"terminal": ["KEYWORD", "IDENTIFIER"]})
            self._eat({"token": ["("]})

            # Need to insert the local arg before the expression list
            if bonusArgs:
                self.vm.writePush("local", localLoc)

            expCount = self.compileExpressionList()

            self.vm.writeCall(funcName, expCount + bonusArgs)
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
            opToken = self.jt.tokens[self.jt.i][0]
            self._compileOp()
            self.compileTerm()
            arith_write = {
                "+": "add",
                "-": "sub",
                "*": "call Math.multiply 2",
                "/": "call Math.divide 2",
                "&": "and",
                "|": "or",
                "<": "lt",
                ">": "gt",
                "=": "eq",
            }.get(opToken)
            self.vm.writeArithmetic(arith_write)

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
        # unaryOp term?
        elif token[0] in ["-", "~"]:
            arith_write = {"-": "neg", "~": "not"}.get(token[0])
            self._eat({"token": ["-", "~"]})
            self.compileTerm()
            self.vm.writeArithmetic(arith_write)
        # subroutine
        elif token_next[0] in ["(", "."]:
            self._subroutineCall()

        # varName [ expression ]
        elif token_next[0] in ["["]:
            self._eat({"terminal": ["IDENTIFIER"]})
            self._eat({"token": ["["]})
            self.compileExpression()
            # Want to push the token
            self._pushHandler(token[0])
            self.vm.writeArithmetic("add")
            self.vm.writePop("pointer", 1)
            self.vm.writePush("that", 0)

            self._eat({"token": ["]"]})

        else:
            if token[1] == "INT_CONST":
                self.vm.writePush("constant", token[0])
            if token[1] == "IDENTIFIER":
                self._pushHandler(token[0])
            elif token[1] == "STRING_CONST":
                str_len = len(token[0])
                self.vm.writePush("constant", str_len)
                self.vm.writeCall("String.new", 1)

                for c in token[0]:
                    self.vm.writePush("constant", ord(c))
                    self.vm.writeCall("String.appendChar", 2)

            elif token[1] == "KEYWORD":
                # null, false, = 0
                # true = -1
                # keywordDict = {"null":0,"false":0,"true":-1}
                if token[0].lower() in ["null", "false"]:
                    self.vm.writePush("constant", 0)
                elif token[0].lower() == "true":
                    self.vm.writePush("constant", 0)
                    self.vm.writeArithmetic("not")
                elif token[0].lower() == "this":
                    self.vm.writePush("pointer", 0)
                else:
                    raise Exception("NOT HANDLED")

            self._eat(
                {"terminal": ["KEYWORD", "IDENTIFIER", "STRING_CONST", "INT_CONST"]}
            )

        self._getCloseTag("term")

    def _getSegmentIndex(self, token):
        kind_dict = {
            "field": "this",
            "static": "static",
            "local": "local",
            "var": "local",
            "argument": "argument",
        }
        if self.symbolTableSubroutine and token in self.symbolTableSubroutine.table:
            segment = self.symbolTableSubroutine.table[token]["kind"]
            ind = self.symbolTableSubroutine.table[token]["number"]
        else:
            segment = self.symbolTableClass.table[token]["kind"]
            ind = self.symbolTableClass.table[token]["number"]

        segment = kind_dict.get(segment)
        if not segment:
            raise Exception("TOKEN NOT FOUND'")
        return segment, ind

    def _pushHandler(self, token):
        segment, index = self._getSegmentIndex(token)
        self.vm.writePush(segment, index)

    def _popHandler(self, token):
        segment, index = self._getSegmentIndex(token)
        self.vm.writePop(segment, index)

    def compileExpressionList(self):
        """
        Compiles a (possibly empty) comma-separated list of expressions
        """
        self._getOpenTag("expressionList")

        expCount = 0

        if self._check_compileExpression():
            expCount += 1
            self.compileExpression()

        while self._check_fields({"token": [","]}):
            self._eat({"token": [","]})
            self.compileExpression()
            expCount += 1

        self._getCloseTag("expressionList")

        return expCount


class JackCompiler:
    def __init__(self, file_or_directory):

        if not os.path.isdir(file_or_directory):
            jt = JackTokenizer(file_or_directory)
            ce = CompilationEngine(jt)
            ce.compile()
            vm_lines = "\n".join(ce.vm.o)
            write_filename = "{}.vm".format(open_file[:-5])
            self.write_file(write_filename, vm_lines)

        else:
            for filename in os.listdir(file_or_directory):
                if filename.endswith(".jack"):
                    open_file = os.path.join(file_or_directory, filename)
                    jt = JackTokenizer(open_file)

                    ce = CompilationEngine(jt)
                    ce.compile()
                    vm_lines = "\n".join(ce.vm.o)
                    write_filename = "{}.vm".format(open_file[:-5])
                    self.write_file(write_filename, vm_lines)

    @staticmethod
    def write_file(filename, f):
        with open(filename, "w") as wf:
            wf.write(f)


class VMWriter:
    def __init__(self):

        self.o = []

    def writePush(self, segment, index):
        self.o.append("push {} {}".format(segment.lower(), index))

    def writePop(self, segment, index):
        self.o.append("pop {} {}".format(segment.lower(), index))

    def writeArithmetic(self, command):
        self.o.append(command)

    def writeLabel(self, label):
        self.o.append("label {}".format(label))

    def writeGoto(self, label):
        self.o.append("goto {}".format(label))

    def writeIf(self, label):
        self.o.append("if-goto {}".format(label))

    def writeCall(self, name, nArgs):
        self.o.append("call {} {}".format(name, nArgs))

    def writeFunction(self, name, nLocals):
        self.o.append("function {} {}".format(name, nLocals))

    def writeReturn(self):
        self.o.append("return")


class SymbolTable:
    """
    Stores symbol tables
    """

    def __init__(self):
        self.table = {}
        self.kind_counts = {}

    def insert(self, name, kind, type_):
        """
        We need to figure out the number - if not in the table 0
        """
        number = self.kind_counts.get(kind, 0)
        self.table[name] = {"type": type_, "kind": kind, "number": number}

        # The counts should be the actual number we've inserted, so indexes match up
        try:
            self.kind_counts[kind] += 1
        except:
            self.kind_counts[kind] = 1


if __name__ == "__main__":
    conv_file = sys.argv[1]
    ja = JackCompiler(conv_file)

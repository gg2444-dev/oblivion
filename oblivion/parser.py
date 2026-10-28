"""Parser da linguagem Oblivion (descida recursiva).

O parser consome a lista de tokens devolvida pelo :mod:`oblivion.lexer` e
monta a árvore sintática abstrata (ver :mod:`oblivion.ast_nodes`). Ele é
escrito à mão com *descida recursiva*: cada nível de precedência tem seu
próprio método. Nada aqui traduz o código para Python.

Gramática EBNF (a real, usada por este arquivo)::

    program        = { NEWLINE | statement } EOF ;

    statement      = letStmt
                   | ifStmt
                   | whileStmt
                   | forStmt
                   | breakStmt
                   | continueStmt
                   | funDecl
                   | returnStmt
                   | assignStmt
                   | exprStmt ;

    letStmt        = "let" IDENT "=" expression lineEnd ;
    assignStmt     = assignTarget "=" expression lineEnd ;
    assignTarget   = IDENT | indexExpr | memberExpr ;   (* lado esquerdo válido *)
    ifStmt         = "if" expression block [ "else" ( ifStmt | block ) ] ;
    whileStmt      = "while" expression block ;
    forStmt        = "for" IDENT "in" expression block ;
    breakStmt      = "break" lineEnd ;         (* só dentro de while/for *)
    continueStmt   = "continue" lineEnd ;      (* só dentro de while/for *)
    funDecl        = "fun" IDENT "(" [ params ] ")" block ;
    params         = IDENT { "," IDENT } ;   (* sem repetidos, máx. 255 *)
    returnStmt     = "return" [ expression ] lineEnd ;   (* só dentro de fun *)
    exprStmt       = expression lineEnd ;
    block          = "{" { NEWLINE | statement } "}" ;
    lineEnd        = NEWLINE | "}" | EOF ;   (* uma instrução por linha *)

    expression     = orExpr ;
    orExpr         = andExpr { "or" andExpr } ;
    andExpr        = notExpr { "and" notExpr } ;
    notExpr        = "not" notExpr | comparison ;
    comparison     = term { ( "==" | "!=" | "<" | "<=" | ">" | ">=" ) term } ;
    term           = factor { ( "+" | "-" ) factor } ;
    factor         = unary { ( "*" | "/" | "//" | "%" ) unary } ;
    unary          = "-" unary | postfix ;
    postfix        = primary { call | indexExpr | memberExpr } ;
    call           = "(" [ args ] ")" ;
    indexExpr      = "[" expression "]" ;
    memberExpr     = "." IDENT ;
    args           = expression { "," expression } ;      (* máx. 255 *)
    primary        = NUMBER
                   | STRING
                   | "true" | "false" | "null"
                   | listLit
                   | mapLit
                   | IDENT
                   | "(" expression ")" ;
    listLit        = "[" [ elements ] "]" ;   (* multilinha: NEWLINEs ignorados *)
    elements       = expression { "," expression } [ "," ] ;
    mapLit         = "{" [ mapEntries ] "}" ;
    mapEntries     = mapEntry { "," mapEntry } [ "," ] ;
    mapEntry       = ( IDENT | STRING ) ":" expression ;

Observações documentais:

* ``not`` tem precedência menor que as comparações e maior que ``and``
  (``not a == b`` significa ``not (a == b)``).
* ``and``/``or`` são avaliados com curto-circuitamento.
* ``return`` fora de função, ``break``/``continue`` fora de laço e
  ``else`` sem ``if`` são erros de sintaxe.
* Listas e mapas podem ocupar várias linhas (as quebras de linha são
  ignoradas dentro de ``[ ]`` e ``{ }`` literais).
* O alvo de ``=`` precisa ser variável, índice ou propriedade; qualquer
  outra expressão à esquerda é erro de sintaxe.
"""
from __future__ import annotations

from .ast_nodes import (
    AssignStatement,
    BlockStatement,
    BooleanLiteral,
    Binary,
    BreakStatement,
    Call,
    ContinueStatement,
    ExpressionStatement,
    ForStatement,
    FunctionDeclaration,
    Grouping,
    IfStatement,
    Index,
    IndexAssign,
    LetStatement,
    ListLiteral,
    Logical,
    MapLiteral,
    Member,
    MemberAssign,
    Node,
    NullLiteral,
    NumberLiteral,
    ReturnStatement,
    StringLiteral,
    Unary,
    Variable,
    WhileStatement,
)
from .errors import OblivionSyntaxError
from .tokens import Token, TokenType

#: Limite de recursos da gramática (parâmetros/argumentos por chamada).
MAX_PARAMS = 255
MAX_ARGUMENTS = 255


class Parser:
    """Analisa uma lista de tokens e devolve a lista de instruções (AST)."""

    def __init__(self, tokens: list[Token], filename: str = "<programa>") -> None:
        self._tokens = tokens
        self._filename = filename
        self._current = 0
        self._function_depth = 0  # para recusar 'return' fora de função
        self._loop_depth = 0      # para recusar 'break'/'continue' fora de laço

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def parse(self) -> list[Node]:
        """Analisa o arquivo inteiro e devolve a lista de instruções."""
        statements: list[Node] = []
        self._skip_newlines()
        while not self._check(TokenType.EOF):
            statements.append(self._statement())
            self._line_end()
            self._skip_newlines()
        return statements

    # ------------------------------------------------------------------
    # Instruções
    # ------------------------------------------------------------------
    def _statement(self) -> Node:
        if self._match(TokenType.LET):
            return self._let_statement()
        if self._check(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.WHILE):
            return self._while_statement()
        if self._match(TokenType.FOR):
            return self._for_statement()
        if self._match(TokenType.BREAK):
            return self._break_statement()
        if self._match(TokenType.CONTINUE):
            return self._continue_statement()
        if self._match(TokenType.FUN):
            return self._function_declaration()
        if self._match(TokenType.RETURN):
            return self._return_statement()
        if self._check(TokenType.RIGHT_BRACE):
            raise self._error(self._peek(), "'}' inesperado (o bloco já foi fechado)")
        if self._check(TokenType.ELSE):
            raise self._error(self._peek(), "'else' sem um 'if' correspondente")
        if self._check(TokenType.LEFT_BRACE):
            raise self._error(
                self._peek(),
                "'{' inesperado: blocos só podem seguir 'if', 'while', 'for' ou 'fun'",
            )
        # Atribuição (x = ..., x[0] = ..., x.prop = ...) é detectada depois de
        # analisar a expressão, em _expression_statement().
        return self._expression_statement()

    def _let_statement(self) -> Node:
        name_tok = self._consume(
            TokenType.IDENTIFIER, "esperava um nome de variável após 'let'"
        )
        self._consume(TokenType.EQUAL, "esperava '=' para dar um valor à variável")
        initializer = self._expression()
        return LetStatement(
            name_tok.lexeme, initializer, line=name_tok.line, column=name_tok.column
        )

    def _expression_statement(self) -> Node:
        expression = self._expression()
        if self._match(TokenType.EQUAL):
            # Atribuição: o lado esquerdo já foi analisado como expressão.
            equals = self._previous()
            value = self._expression()
            if isinstance(expression, Variable):
                return AssignStatement(
                    expression.name, value, line=expression.line, column=expression.column
                )
            if isinstance(expression, Index):
                return IndexAssign(expression, value, line=expression.line, column=expression.column)
            if isinstance(expression, Member):
                return MemberAssign(expression, value, line=expression.line, column=expression.column)
            raise self._error(
                equals,
                "lado esquerdo inválido para '=': use uma variável, um índice "
                "(lista[0]) ou uma propriedade (mapa.nome)",
            )
        return ExpressionStatement(
            expression, line=expression.line, column=expression.column
        )

    def _if_statement(self) -> Node:
        keyword = self._consume(TokenType.IF, "esperava 'if'")
        condition = self._expression()
        then_block = self._block()
        else_branch: Node | None = None

        # 'else' pode estar na mesma linha do '}' ou na linha seguinte.
        saved = self._current
        self._skip_newlines()
        if self._match(TokenType.ELSE):
            if self._check(TokenType.IF):
                else_branch = self._if_statement()  # else if encadeado
            else:
                else_branch = self._block()
        else:
            self._current = saved  # não havia else: desfaz a varredura

        return IfStatement(
            condition, then_block, else_branch, line=keyword.line, column=keyword.column
        )

    def _while_statement(self) -> Node:
        keyword = self._previous()
        condition = self._expression()
        self._loop_depth += 1
        body = self._block()
        self._loop_depth -= 1
        return WhileStatement(condition, body, line=keyword.line, column=keyword.column)

    def _for_statement(self) -> Node:
        keyword = self._previous()
        name_tok = self._consume(
            TokenType.IDENTIFIER, "esperava um nome de variável após 'for'"
        )
        self._consume(TokenType.IN, "esperava 'in' após o nome da variável")
        iterable = self._expression()
        self._loop_depth += 1
        body = self._block()
        self._loop_depth -= 1
        return ForStatement(
            name_tok.lexeme, iterable, body, line=keyword.line, column=keyword.column
        )

    def _break_statement(self) -> Node:
        keyword = self._previous()
        if self._loop_depth == 0:
            raise self._error(keyword, "'break' só pode ser usado dentro de um laço")
        return BreakStatement(line=keyword.line, column=keyword.column)

    def _continue_statement(self) -> Node:
        keyword = self._previous()
        if self._loop_depth == 0:
            raise self._error(keyword, "'continue' só pode ser usado dentro de um laço")
        return ContinueStatement(line=keyword.line, column=keyword.column)

    def _function_declaration(self) -> Node:
        name_tok = self._consume(
            TokenType.IDENTIFIER, "esperava um nome de função após 'fun'"
        )
        self._consume(TokenType.LEFT_PAREN, "esperava '(' após o nome da função")

        params: list[str] = []
        if not self._check(TokenType.RIGHT_PAREN):
            while True:
                param_tok = self._consume(
                    TokenType.IDENTIFIER, "esperava um nome de parâmetro"
                )
                if param_tok.lexeme in params:
                    raise self._error(
                        param_tok, f"parâmetro repetido '{param_tok.lexeme}'"
                    )
                if len(params) >= MAX_PARAMS:
                    raise self._error(param_tok, f"máximo de {MAX_PARAMS} parâmetros")
                params.append(param_tok.lexeme)
                if not self._match(TokenType.COMMA):
                    break
        self._consume(
            TokenType.RIGHT_PAREN, "esperava ')' após os parâmetros da função"
        )

        # Uma função nova 'esquece' os laços ao redor: 'break' dentro de uma
        # função não pode sair de um laço que está fora dela.
        saved_loop_depth = self._loop_depth
        self._loop_depth = 0
        self._function_depth += 1
        body = self._block()
        self._function_depth -= 1
        self._loop_depth = saved_loop_depth

        return FunctionDeclaration(
            name_tok.lexeme, params, body, line=name_tok.line, column=name_tok.column
        )

    def _return_statement(self) -> Node:
        keyword = self._previous()
        if self._function_depth == 0:
            raise self._error(keyword, "'return' só pode ser usado dentro de uma função")
        value: Node | None = None
        if not (
            self._check(TokenType.NEWLINE)
            or self._check(TokenType.RIGHT_BRACE)
            or self._check(TokenType.EOF)
        ):
            value = self._expression()
        return ReturnStatement(value, line=keyword.line, column=keyword.column)

    def _block(self) -> BlockStatement:
        lbrace = self._consume(TokenType.LEFT_BRACE, "esperava '{' para abrir o bloco")
        statements: list[Node] = []
        self._skip_newlines()
        while not self._check(TokenType.RIGHT_BRACE) and not self._check(TokenType.EOF):
            statements.append(self._statement())
            self._line_end()
            self._skip_newlines()
        self._consume(TokenType.RIGHT_BRACE, "esperava '}' para fechar o bloco")
        return BlockStatement(statements, line=lbrace.line, column=lbrace.column)

    def _line_end(self) -> None:
        """Exige o fim da instrução (uma instrução por linha)."""
        if self._match(TokenType.NEWLINE):
            return
        if self._check(TokenType.RIGHT_BRACE) or self._check(TokenType.EOF):
            return
        raise self._error(
            self._peek(), "esperava o fim da linha (cada instrução ocupa uma linha)"
        )

    # ------------------------------------------------------------------
    # Expressões (uma função por nível de precedência)
    # ------------------------------------------------------------------
    def _expression(self) -> Node:
        return self._or()

    def _or(self) -> Node:
        left = self._and()
        while self._match(TokenType.OR):
            operator = self._previous()
            right = self._and()
            left = Logical(
                left, operator.lexeme, right, line=operator.line, column=operator.column
            )
        return left

    def _and(self) -> Node:
        left = self._not()
        while self._match(TokenType.AND):
            operator = self._previous()
            right = self._not()
            left = Logical(
                left, operator.lexeme, right, line=operator.line, column=operator.column
            )
        return left

    def _not(self) -> Node:
        if self._match(TokenType.NOT):
            operator = self._previous()
            operand = self._not()
            return Unary(
                operator.lexeme, operand, line=operator.line, column=operator.column
            )
        return self._comparison()

    def _comparison(self) -> Node:
        left = self._term()
        while self._match(
            TokenType.EQUAL_EQUAL,
            TokenType.BANG_EQUAL,
            TokenType.LESS,
            TokenType.LESS_EQUAL,
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
        ):
            operator = self._previous()
            right = self._term()
            left = Binary(
                left, operator.lexeme, right, line=operator.line, column=operator.column
            )
        return left

    def _term(self) -> Node:
        left = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = self._previous()
            right = self._factor()
            left = Binary(
                left, operator.lexeme, right, line=operator.line, column=operator.column
            )
        return left

    def _factor(self) -> Node:
        left = self._unary()
        while self._match(
            TokenType.STAR, TokenType.SLASH, TokenType.SLASH_SLASH, TokenType.PERCENT
        ):
            operator = self._previous()
            right = self._unary()
            left = Binary(
                left, operator.lexeme, right, line=operator.line, column=operator.column
            )
        return left

    def _unary(self) -> Node:
        if self._match(TokenType.MINUS):
            operator = self._previous()
            operand = self._unary()
            return Unary(
                operator.lexeme, operand, line=operator.line, column=operator.column
            )
        return self._call()

    def _call(self) -> Node:
        """Chamadas, indexações e propriedades encadeadas: f(x)[0].prop."""
        expression = self._primary()
        while True:
            if self._match(TokenType.LEFT_PAREN):
                lparen = self._previous()
                arguments: list[Node] = []
                if not self._check(TokenType.RIGHT_PAREN):
                    while True:
                        if len(arguments) >= MAX_ARGUMENTS:
                            raise self._error(
                                lparen, f"máximo de {MAX_ARGUMENTS} argumentos por chamada"
                            )
                        arguments.append(self._expression())
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(
                    TokenType.RIGHT_PAREN, "esperava ')' após os argumentos da chamada"
                )
                expression = Call(
                    expression, arguments, line=expression.line, column=expression.column
                )
            elif self._match(TokenType.LEFT_BRACKET):
                lbracket = self._previous()
                index = self._expression()
                self._consume(TokenType.RIGHT_BRACKET, "esperava ']' após o índice")
                expression = Index(
                    expression, index, line=expression.line, column=expression.column
                )
            elif self._match(TokenType.DOT):
                self._consume(
                    TokenType.IDENTIFIER, "esperava um nome de propriedade após '.'"
                )
                name_tok = self._previous()
                expression = Member(
                    expression, name_tok.lexeme, line=expression.line, column=expression.column
                )
            else:
                return expression

    def _primary(self) -> Node:
        if self._match(TokenType.NUMBER):
            token = self._previous()
            return NumberLiteral(token.literal, line=token.line, column=token.column)
        if self._match(TokenType.STRING):
            token = self._previous()
            return StringLiteral(token.literal, line=token.line, column=token.column)
        if self._match(TokenType.TRUE):
            token = self._previous()
            return BooleanLiteral(True, line=token.line, column=token.column)
        if self._match(TokenType.FALSE):
            token = self._previous()
            return BooleanLiteral(False, line=token.line, column=token.column)
        if self._match(TokenType.NULL):
            token = self._previous()
            return NullLiteral(line=token.line, column=token.column)
        if self._match(TokenType.IDENTIFIER):
            token = self._previous()
            return Variable(token.lexeme, line=token.line, column=token.column)
        if self._match(TokenType.LEFT_PAREN):
            lparen = self._previous()
            expression = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "esperava ')' após a expressão")
            return Grouping(expression, line=lparen.line, column=lparen.column)
        if self._match(TokenType.LEFT_BRACKET):
            return self._list_literal()
        if self._match(TokenType.LEFT_BRACE):
            return self._map_literal()
        raise self._error(self._peek(), "esperava uma expressão")

    def _list_literal(self) -> Node:
        """``[a, b, c]`` — pode ocupar várias linhas (NEWLINEs são ignorados)."""
        lbracket = self._previous()
        elements: list[Node] = []
        self._skip_newlines()
        if not self._check(TokenType.RIGHT_BRACKET):
            while True:
                elements.append(self._expression())
                self._skip_newlines()
                if not self._match(TokenType.COMMA):
                    break
                self._skip_newlines()
                if self._check(TokenType.RIGHT_BRACKET):
                    break  # vírgula final opcional: [1, 2,]
        self._consume(TokenType.RIGHT_BRACKET, "esperava ']' para fechar a lista")
        return ListLiteral(elements, line=lbracket.line, column=lbracket.column)

    def _map_literal(self) -> Node:
        """``{ chave: valor }`` — pode ocupar várias linhas (usado em expressões;
        na posição de instrução, ``{`` continua sendo erro de sintaxe)."""
        lbrace = self._previous()
        pairs: dict[str, Node] = {}
        self._skip_newlines()
        if not self._check(TokenType.RIGHT_BRACE):
            while True:
                key_tok = self._advance()
                if key_tok.type is TokenType.IDENTIFIER:
                    key = key_tok.lexeme
                elif key_tok.type is TokenType.STRING:
                    key = key_tok.literal
                else:
                    raise self._error(
                        key_tok, "esperava um nome ou um texto como chave do mapa"
                    )
                if key in pairs:
                    raise self._error(key_tok, f"chave repetida '{key}'")
                self._consume(TokenType.COLON, "esperava ':' entre a chave e o valor")
                pairs[key] = self._expression()
                self._skip_newlines()
                if not self._match(TokenType.COMMA):
                    break
                self._skip_newlines()
                if self._check(TokenType.RIGHT_BRACE):
                    break  # vírgula final opcional
        self._consume(TokenType.RIGHT_BRACE, "esperava '}' para fechar o mapa")
        return MapLiteral(pairs, line=lbrace.line, column=lbrace.column)

    # ------------------------------------------------------------------
    # Utilitários de navegação nos tokens
    # ------------------------------------------------------------------
    def _match(self, *types: TokenType) -> bool:
        for type_ in types:
            if self._check(type_):
                self._advance()
                return True
        return False

    def _consume(self, type_: TokenType, message: str) -> Token:
        if self._check(type_):
            return self._advance()
        raise self._error(self._peek(), message)

    def _check(self, type_: TokenType) -> bool:
        return self._peek().type is type_

    def _check_next(self, type_: TokenType) -> bool:
        return self._peek_next().type is type_

    def _advance(self) -> Token:
        if not self._at_end():
            self._current += 1
        return self._previous()

    def _at_end(self) -> bool:
        return self._peek().type is TokenType.EOF

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _peek_next(self) -> Token:
        if self._current + 1 < len(self._tokens):
            return self._tokens[self._current + 1]
        return self._tokens[-1]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _skip_newlines(self) -> None:
        while self._match(TokenType.NEWLINE):
            pass

    def _describe(self, token: Token) -> str:
        if token.type is TokenType.EOF:
            return "o fim do arquivo"
        if token.type is TokenType.NEWLINE:
            return "o fim da linha"
        return repr(token.lexeme)

    def _error(self, token: Token, message: str) -> OblivionSyntaxError:
        return OblivionSyntaxError(
            f"{message} (encontrado {self._describe(token)})",
            filename=self._filename,
            line=token.line,
            column=token.column,
        )

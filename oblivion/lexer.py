"""Analisador léxico (lexer) da linguagem Oblivion.

O lexer varre o código-fonte caractere por caractere e produz a lista de
tokens que o parser consome. Ele também:

* ignora espaços, tabulações e comentários que começam com ``#``;
* emite tokens ``NEWLINE`` (a linguagem tem uma instrução por linha),
  exceto quando está dentro de parênteses — assim expressões podem ser
  quebras em várias linhas;
* reporta caracteres inválidos, strings não terminadas e escapes
  desconhecidos como erros léxicos com linha e coluna.
"""
from __future__ import annotations

from typing import NoReturn

from .errors import OblivionLexError
from .tokens import KEYWORDS, Token, TokenType

_ESCAPES: dict[str, str] = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "\\": "\\",
    '"': '"',
    "'": "'",
}


class Lexer:
    """Converte código-fonte Oblivion em uma lista de tokens."""

    def __init__(self, source: str, filename: str = "<fonte>") -> None:
        # Remove um eventual BOM (comum em arquivos UTF-8 salvos no Windows).
        self.source = source[1:] if source.startswith("\ufeff") else source
        self.filename = filename
        self._tokens: list[Token] = []
        self._current = 0        # índice do próximo caractere a ler
        self._line = 1           # linha atual (1-based)
        self._line_start = 0     # índice do primeiro caractere da linha atual
        self._paren_depth = 0    # profundidade de parênteses (suprime NEWLINE)
        # Posição do token que está sendo reconhecido agora:
        self._token_start = 0
        self._token_line = 1
        self._token_column = 1

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def tokenize(self) -> list[Token]:
        """Analisa todo o código e devolve a lista de tokens (terminada em EOF)."""
        while not self._at_end():
            self._token_start = self._current
            self._token_line = self._line
            self._token_column = self._current - self._line_start + 1
            self._scan_token()
        self._tokens.append(
            Token(TokenType.EOF, "", None, self._line, self._current - self._line_start + 1)
        )
        return self._tokens

    # ------------------------------------------------------------------
    # Varredura de um único token
    # ------------------------------------------------------------------
    def _scan_token(self) -> None:
        c = self._advance()

        # Espaços em branco (o \r cobre arquivos com fim de linha Windows).
        if c in " \t\r\f\v":
            return

        if c == "\n":
            if self._paren_depth == 0:
                self._add_token(TokenType.NEWLINE, "\n")
            self._line += 1
            self._line_start = self._current
            return

        if c == "#":
            # Comentário: vai até o fim da linha (o \n é tratado acima).
            while not self._at_end() and self._peek() != "\n":
                self._advance()
            return

        if c in "\"'":
            self._string(c)
            return

        if c.isascii() and c.isdigit():
            self._number()
            return

        if c.isascii() and (c.isalpha() or c == "_"):
            self._identifier()
            return

        # Pontuação e operadores de um/dois caracteres.
        if c == "(":
            self._paren_depth += 1
            self._add_token(TokenType.LEFT_PAREN, "(")
        elif c == ")":
            if self._paren_depth > 0:
                self._paren_depth -= 1
            self._add_token(TokenType.RIGHT_PAREN, ")")
        elif c == "{":
            self._add_token(TokenType.LEFT_BRACE, "{")
        elif c == "}":
            self._add_token(TokenType.RIGHT_BRACE, "}")
        elif c == ",":
            self._add_token(TokenType.COMMA, ",")
        elif c == "[":
            self._add_token(TokenType.LEFT_BRACKET, "[")
        elif c == "]":
            self._add_token(TokenType.RIGHT_BRACKET, "]")
        elif c == ":":
            self._add_token(TokenType.COLON, ":")
        elif c == ".":
            # O '.' só chega aqui fora de números (2.5 é consumido pelo _number).
            self._add_token(TokenType.DOT, ".")
        elif c == "+":
            self._add_token(TokenType.PLUS, "+")
        elif c == "-":
            self._add_token(TokenType.MINUS, "-")
        elif c == "*":
            self._add_token(TokenType.STAR, "*")
        elif c == "%":
            self._add_token(TokenType.PERCENT, "%")
        elif c == "/":
            if self._match("/"):
                self._add_token(TokenType.SLASH_SLASH, "//")
            else:
                self._add_token(TokenType.SLASH, "/")
        elif c == "=":
            if self._match("="):
                self._add_token(TokenType.EQUAL_EQUAL, "==")
            else:
                self._add_token(TokenType.EQUAL, "=")
        elif c == "!":
            if self._match("="):
                self._add_token(TokenType.BANG_EQUAL, "!=")
            else:
                self._fail("'!' sozinho não existe; use '!=' para 'diferente de'")
        elif c == "<":
            if self._match("="):
                self._add_token(TokenType.LESS_EQUAL, "<=")
            else:
                self._add_token(TokenType.LESS, "<")
        elif c == ">":
            if self._match("="):
                self._add_token(TokenType.GREATER_EQUAL, ">=")
            else:
                self._add_token(TokenType.GREATER, ">")
        else:
            hint = ""
            if c == "&":
                hint = " (use 'and' para o E lógico)"
            elif c == "|":
                hint = " (use 'or' para o OU lógico)"
            elif not c.isascii():
                hint = " (caracteres fora da tabela ASCII só são permitidos dentro de textos)"
            self._fail(f"caractere inválido {c!r}{hint}")

    def _string(self, quote: str) -> None:
        """Lê uma string delimitada por aspas (simples ou duplas)."""
        chars: list[str] = []
        while not self._at_end():
            ch = self._peek()
            if ch == quote:
                self._advance()
                lexeme = self.source[self._token_start:self._current]
                self._add_token(TokenType.STRING, lexeme, "".join(chars))
                return
            if ch == "\n":
                self._fail("string não terminada (faltou a aspa que fecha a linha)")
            if ch == "\\":
                self._advance()
                if self._at_end() or self._peek() == "\n":
                    self._fail("string não terminada depois de uma barra invertida '\\'")
                esc = self._advance()
                if esc not in _ESCAPES:
                    self._fail(
                        f"sequência de escape inválida '\\{esc}' "
                        r"(use \n, \t, \r, \\, \" ou \')"
                    )
                chars.append(_ESCAPES[esc])
            else:
                chars.append(self._advance())
        self._fail("string não terminada (faltou a aspa que fecha o texto)")

    def _number(self) -> None:
        """Lê um número inteiro ou decimal (sem notação de exponência em v0.2)."""
        start = self._current - 1
        while self._peek().isascii() and self._peek().isdigit():
            self._advance()
        if self._peek() == "." and self._peek_next().isascii() and self._peek_next().isdigit():
            self._advance()  # consome o ponto
            while self._peek().isascii() and self._peek().isdigit():
                self._advance()
        lexeme = self.source[start:self._current]
        value: int | float = float(lexeme) if "." in lexeme else int(lexeme)
        self._add_token(TokenType.NUMBER, lexeme, value)

    def _identifier(self) -> None:
        """Lê um identificador e verifica se ele é uma palavra-chave."""
        start = self._current - 1
        while True:
            ch = self._peek()
            if ch.isascii() and (ch.isalpha() or ch.isdigit() or ch == "_"):
                self._advance()
            else:
                break
        lexeme = self.source[start:self._current]
        self._add_token(KEYWORDS.get(lexeme, TokenType.IDENTIFIER), lexeme, None)

    # ------------------------------------------------------------------
    # Utilitários de leitura
    # ------------------------------------------------------------------
    def _add_token(self, type_: TokenType, lexeme: str, literal: object = None) -> None:
        self._tokens.append(
            Token(type_, lexeme, literal, self._token_line, self._token_column)
        )

    def _fail(self, message: str) -> NoReturn:
        """Levanta um erro léxico apontando o início do token problemático."""
        raise OblivionLexError(
            message, filename=self.filename, line=self._token_line, column=self._token_column
        )

    def _at_end(self) -> bool:
        return self._current >= len(self.source)

    def _peek(self) -> str:
        return "\0" if self._at_end() else self.source[self._current]

    def _peek_next(self) -> str:
        return "\0" if self._current + 1 >= len(self.source) else self.source[self._current + 1]

    def _advance(self) -> str:
        ch = self.source[self._current]
        self._current += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._at_end() or self.source[self._current] != expected:
            return False
        self._current += 1
        return True

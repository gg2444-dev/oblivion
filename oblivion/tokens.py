"""Definição de tokens da linguagem Oblivion.

Um token é a menor unidade com significado do código-fonte: um número,
um nome, uma palavra-chave ou um operador. Cada token guarda a linha e a
coluna onde começou, para que os erros possam apontar exatamente o lugar
do arquivo.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    """Todos os tipos de token possíveis em Oblivion v0.2."""

    # --- literais ---
    NUMBER = auto()      # 42, 3.14
    STRING = auto()      # "texto" ou 'texto'
    IDENTIFIER = auto()  # nomes de variáveis e funções

    # --- palavras-chave ---
    LET = auto()     # declaração de variável
    IF = auto()      # condicional
    ELSE = auto()    # ramo alternativo do if
    WHILE = auto()   # laço de repetição (condição)
    FOR = auto()     # laço de repetição (percorre coleções)
    IN = auto()      # 'for x in colecao'
    BREAK = auto()   # sai do laço
    CONTINUE = auto()  # pula para a próxima iteração
    FUN = auto()     # declaração de função
    RETURN = auto()  # retorno de função
    TRUE = auto()    # literal true
    FALSE = auto()   # literal false
    NULL = auto()    # literal null
    AND = auto()     # E lógico
    OR = auto()      # OU lógico
    NOT = auto()     # NÃO lógico

    # --- operadores ---
    PLUS = auto()         # +
    MINUS = auto()        # -
    STAR = auto()         # *
    SLASH = auto()        # /
    SLASH_SLASH = auto()  # //
    PERCENT = auto()      # %
    EQUAL = auto()        # =
    EQUAL_EQUAL = auto()  # ==
    BANG_EQUAL = auto()   # !=
    LESS = auto()         # <
    LESS_EQUAL = auto()   # <=
    GREATER = auto()      # >
    GREATER_EQUAL = auto()  # >=

    # --- pontuação ---
    LEFT_PAREN = auto()   # (
    RIGHT_PAREN = auto()  # )
    LEFT_BRACE = auto()   # {
    RIGHT_BRACE = auto()  # }
    LEFT_BRACKET = auto()   # [
    RIGHT_BRACKET = auto()  # ]
    COMMA = auto()        # ,
    COLON = auto()        # : (chave: valor nos mapas)
    DOT = auto()          # . (propriedade: profile.name)

    # --- estrutura do arquivo ---
    NEWLINE = auto()  # fim de linha (uma instrução por linha)
    EOF = auto()      # fim do arquivo


#: Palavras-chave reservadas da linguagem (inglês, minúsculas).
KEYWORDS: dict[str, TokenType] = {
    "let": TokenType.LET,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "fun": TokenType.FUN,
    "return": TokenType.RETURN,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
}


@dataclass(frozen=True)
class Token:
    """Um token com seu tipo, texto original e posição no arquivo."""

    type: TokenType
    lexeme: str       # texto exato como escrito no código
    literal: Any      # valor Python (número/texto) quando faz sentido
    line: int         # linha (começa em 1)
    column: int       # coluna (começa em 1)

    def __str__(self) -> str:
        return f"Token({self.type.name}, {self.lexeme!r}, {self.line}:{self.column})"

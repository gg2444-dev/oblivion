"""Oblivion — linguagem de programação moderna, simples e educacional.

Este pacote contém o interpretador completo da linguagem Oblivion v0.2:

* :mod:`oblivion.lexer` / :mod:`oblivion.tokens` — tokenização;
* :mod:`oblivion.parser` / :mod:`oblivion.ast_nodes` — gramática e AST;
* :mod:`oblivion.interpreter` — execução do programa;
* :mod:`oblivion.errors` — erros com arquivo, linha e coluna.

Uso rápido (na raiz do projeto)::

    python -m oblivion examples/hello.obl

Nada aqui usa ``eval``/``exec`` do Python para rodar código Oblivion.
"""
from __future__ import annotations

from typing import Callable

from .ast_nodes import Node
from .errors import (
    OblivionError,
    OblivionLexError,
    OblivionRuntimeError,
    OblivionSyntaxError,
)
from .interpreter import DEFAULT_MAX_STEPS, Interpreter, format_value, type_name
from .lexer import Lexer
from .parser import Parser
from .tokens import Token, TokenType

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_MAX_STEPS",
    "Interpreter",
    "Lexer",
    "OblivionError",
    "OblivionLexError",
    "OblivionRuntimeError",
    "OblivionSyntaxError",
    "Parser",
    "Token",
    "TokenType",
    "__version__",
    "format_value",
    "parse_source",
    "run_source",
    "tokenize",
    "type_name",
]


def tokenize(source: str, filename: str = "<fonte>") -> list[Token]:
    """Converte o código-fonte em tokens (etapa léxica)."""
    return Lexer(source, filename).tokenize()


def parse_source(source: str, filename: str = "<fonte>") -> list[Node]:
    """Converte o código-fonte em uma lista de instruções (AST)."""
    tokens = tokenize(source, filename)
    return Parser(tokens, filename).parse()


def run_source(
    source: str,
    filename: str = "<programa>",
    output: Callable[[str], None] | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    interpreter: Interpreter | None = None,
) -> Interpreter:
    """Analisa e executa código Oblivion.

    Parâmetros
    ----------
    source:
        Código-fonte Oblivion.
    filename:
        Nome mostrado nas mensagens de erro.
    output:
        Função chamada pelo ``print`` (padrão: a função ``print`` do Python).
    max_steps:
        Limite de passos de execução (protege contra laços infinitos).
    interpreter:
        Interpretador reutilizado — usado pelo REPL para manter as variáveis.

    Levanta :class:`OblivionLexError`, :class:`OblivionSyntaxError` ou
    :class:`OblivionRuntimeError` conforme a etapa em que o problema ocorrer.
    """
    try:
        program = parse_source(source, filename)
    except RecursionError:
        raise OblivionSyntaxError(
            "código complexo demais: profundidade máxima de aninhamento excedida",
            filename=filename,
        ) from None

    if interpreter is None:
        interpreter = Interpreter(output=output, max_steps=max_steps, filename=filename)
    try:
        interpreter.run(program)
    except RecursionError:
        raise OblivionRuntimeError(
            "profundidade de recursão excedida — verifique se a função tem caso base",
            filename=filename,
        ) from None
    return interpreter

"""Erros da linguagem Oblivion.

Todos os erros mostrados ao usuário herdam de :class:`OblivionError` e
carregam arquivo, linha e coluna quando disponíveis. O interpretador nunca
deixa rastros (tracebacks) do Python aparecerem para erros normais da
linguagem: a mensagem segue o formato::

    arquivo:linha:coluna: tipo: mensagem
"""
from __future__ import annotations


class OblivionError(Exception):
    """Classe base de todos os erros reportados ao usuário."""

    #: Texto curto que identifica a categoria do erro na mensagem.
    kind: str = "erro"

    def __init__(
        self,
        message: str,
        *,
        filename: str = "<programa>",
        line: int = 0,
        column: int = 0,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.filename = filename
        self.line = line
        self.column = column

    def __str__(self) -> str:
        if self.line > 0 and self.column > 0:
            return f"{self.filename}:{self.line}:{self.column}: {self.kind}: {self.message}"
        return f"{self.filename}: {self.kind}: {self.message}"


class OblivionLexError(OblivionError):
    """Erro encontrado durante a tokenização (caracteres inválidos, strings abertas...)."""

    kind = "erro léxico"


class OblivionSyntaxError(OblivionError):
    """Erro encontrado durante a análise sintática (a forma do código está errada)."""

    kind = "erro de sintaxe"


class OblivionRuntimeError(OblivionError):
    """Erro encontrado durante a execução (variável inexistente, tipos incompatíveis...)."""

    kind = "erro em tempo de execução"

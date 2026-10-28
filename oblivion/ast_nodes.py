"""Nodos da árvore sintática abstrata (AST) de Oblivion.

Depois de o parser analisar o código, ele monta uma árvore feita destes
nodos. O interpretador percorre a árvore para executar o programa — o
código Oblivion **nunca** é convertido em código Python.

Hierarquia::

    Node
    ├── Expressões
    │   ├── NumberLiteral / StringLiteral / BooleanLiteral / NullLiteral
    │   ├── ListLiteral           ([1, 2, 3])
    │   ├── MapLiteral            ({ chave: valor })
    │   ├── Variable              (leitura de variável)
    │   ├── Grouping              (expressão entre parênteses)
    │   ├── Unary                 (-x, not x)
    │   ├── Binary                (1 + 2, a < b, ...)
    │   ├── Logical               (a and b, a or b)
    │   ├── Call                  (f(x, y))
    │   ├── Index                 (lista[i], mapa[chave])
    │   └── Member                (mapa.propriedade)
    └── Instruções
        ├── LetStatement          (let x = 1)
        ├── AssignStatement       (x = 1)
        ├── IndexAssign           (lista[0] = v / mapa["k"] = v)
        ├── MemberAssign          (mapa.prop = v)
        ├── ExpressionStatement   (expressão usada como instrução, ex.: print(...))
        ├── BlockStatement        ({ ... })
        ├── IfStatement           (if / else)
        ├── WhileStatement        (while)
        ├── ForStatement          (for x in colecao)
        ├── BreakStatement        (break)
        ├── ContinueStatement     (continue)
        ├── FunctionDeclaration   (fun nome(a, b) { ... })
        └── ReturnStatement       (return valor)
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """Base de todos os nodos; guarda onde o trecho começou no arquivo."""

    line: int = field(default=0, kw_only=True)
    column: int = field(default=0, kw_only=True)


# ----------------------------------------------------------------------
# Expressões
# ----------------------------------------------------------------------
@dataclass
class NumberLiteral(Node):
    """Número literal: ``42`` ou ``3.14``."""

    value: int | float


@dataclass
class StringLiteral(Node):
    """Texto literal: ``"oi"`` ou ``'oi'``."""

    value: str


@dataclass
class BooleanLiteral(Node):
    """Literal booleano: ``true`` ou ``false``."""

    value: bool


@dataclass
class NullLiteral(Node):
    """Literal que representa ausência de valor: ``null``."""


@dataclass
class ListLiteral(Node):
    """Lista literal: ``[1, "dois", null]``."""

    elements: list[Node]


@dataclass
class MapLiteral(Node):
    """Mapa literal: ``{ nome: "Ana", idade: 3 }`` (chaves são textos)."""

    pairs: dict[str, Node]


@dataclass
class Variable(Node):
    """Leitura do valor de uma variável."""

    name: str


@dataclass
class Grouping(Node):
    """Expressão entre parênteses (usada só para agrupar/clarear)."""

    expression: Node


@dataclass
class Unary(Node):
    """Operador unário: ``-valor`` ou ``not valor``."""

    operator: str
    operand: Node


@dataclass
class Binary(Node):
    """Operador de dois operandos: ``+ - * / // % == != < <= > >=``."""

    left: Node
    operator: str
    right: Node


@dataclass
class Logical(Node):
    """Operadores lógicos ``and`` e ``or`` (curto-circuitam)."""

    left: Node
    operator: str
    right: Node


@dataclass
class Call(Node):
    """Chamada de função: ``callee(arg1, arg2, ...)``."""

    callee: Node
    arguments: list[Node]


@dataclass
class Index(Node):
    """Indexação: ``lista[i]`` ou ``mapa["chave"]``."""

    target: Node
    index: Node


@dataclass
class Member(Node):
    """Acesso por propriedade: ``mapa.nome`` (equivale a ``mapa["nome"]``)."""

    target: Node
    name: str


# ----------------------------------------------------------------------
# Instruções
# ----------------------------------------------------------------------
@dataclass
class LetStatement(Node):
    """``let nome = expressão`` — declara uma variável no escopo atual."""

    name: str
    initializer: Node


@dataclass
class AssignStatement(Node):
    """``nome = expressão`` — atribui a uma variável já declarada."""

    name: str
    value: Node


@dataclass
class IndexAssign(Node):
    """``alvo[índice] = valor`` — atribui um elemento de lista ou uma chave de mapa."""

    target: Index
    value: Node


@dataclass
class MemberAssign(Node):
    """``mapa.propriedade = valor`` — cria ou atualiza uma propriedade do mapa."""

    target: Member
    value: Node


@dataclass
class ExpressionStatement(Node):
    """Expressão usada como instrução; o valor é avaliado e descartado."""

    expression: Node


@dataclass
class BlockStatement(Node):
    """Sequência de instruções entre chaves ``{ ... }`` (cria um escopo)."""

    statements: list[Node]


@dataclass
class IfStatement(Node):
    """``if cond { ... } else { ... }``; ``else_branch`` pode ser outro if."""

    condition: Node
    then_block: BlockStatement
    else_branch: Node | None


@dataclass
class WhileStatement(Node):
    """``while cond { ... }`` — repete enquanto a condição for verdadeira."""

    condition: Node
    body: BlockStatement


@dataclass
class ForStatement(Node):
    """``for nome in colecao { ... }`` — percorre lista, mapa (chaves) ou texto."""

    name: str
    iterable: Node
    body: BlockStatement


@dataclass
class BreakStatement(Node):
    """``break`` — sai do laço mais interno (só dentro de while/for)."""


@dataclass
class ContinueStatement(Node):
    """``continue`` — pula para a próxima iteração do laço mais interno."""


@dataclass
class FunctionDeclaration(Node):
    """``fun nome(p1, p2) { ... }`` — declara uma função no escopo atual."""

    name: str
    params: list[str]
    body: BlockStatement


@dataclass
class ReturnStatement(Node):
    """``return expressão`` (ou apenas ``return``) dentro de uma função."""

    value: Node | None

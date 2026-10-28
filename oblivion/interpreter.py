"""Interpretador (runtime) da linguagem Oblivion.

Percorre a AST produzida pelo parser e executa o programa diretamente —
sem usar ``eval``/``exec`` do Python e sem expor builtins do host.

Pontos principais:

* :class:`Environment` — escopo de variáveis com encadeamento (pai/filho);
* :class:`Interpreter` — avalia expressões e executa instruções;
* limites de segurança: número máximo de passos de execução e tamanho
  máximo de texto gerado por concatenação;
* erros de tempo de execução viram :class:`OblivionRuntimeError` com
  arquivo, linha e coluna — nunca um traceback do Python.

Variáveis em Oblivion são **mutáveis**: ``let`` declara e ``=``
atribui novamente (ver README).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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
from .errors import OblivionRuntimeError

#: Limite padrão de passos de execução (protege contra laços infinitos).
DEFAULT_MAX_STEPS = 1_000_000
#: Tamanho máximo de um texto gerado por concatenação (evita consumir memória).
MAX_STRING_LENGTH = 1_000_000
#: Tamanho máximo de listas e mapas (evita consumir memória).
MAX_COLLECTION_LENGTH = 1_000_000
#: Profundidade máxima ao formatar coleções aninhadas no print.
_MAX_FORMAT_DEPTH = 16
#: Nomes de funções embutidas (não podem ser redeclarados nem recebem atribuição).
BUILTIN_NAMES = frozenset({"print", "len", "push"})


# ----------------------------------------------------------------------
# Valores de função
# ----------------------------------------------------------------------
@dataclass
class FunctionValue:
    """Função declarada com ``fun`` no usuário."""

    name: str
    params: list[str]
    body: BlockStatement
    declaration_env: "Environment"

    def __str__(self) -> str:
        return f"<fun {self.name}>"


@dataclass
class BuiltinFunction:
    """Função embutida do interpretador (print, len)."""

    name: str
    min_args: int
    max_args: int | None  # None = quantos quiser
    implementation: Callable[[list[Any], Node], Any]

    def __str__(self) -> str:
        return f"<fun {self.name}>"


# ----------------------------------------------------------------------
# Escopo de variáveis
# ----------------------------------------------------------------------
class Environment:
    """Um escopo: variáveis declaradas aqui + referência ao escopo pai."""

    def __init__(self, parent: "Environment | None" = None) -> None:
        self.values: dict[str, Any] = {}
        self.parent = parent

    def declare(
        self, name: str, value: Any, node: Node | None = None, filename: str = "<programa>"
    ) -> None:
        """Declara ``name`` neste escopo (erro se já existir aqui)."""
        if name in BUILTIN_NAMES:
            raise _runtime_error(
                filename,
                node,
                f"'{name}' é uma função embutida e não pode ser redeclarada",
            )
        if name in self.values:
            raise _runtime_error(
                filename, node, f"variável '{name}' já foi declarada neste escopo"
            )
        self.values[name] = value

    def declare_raw(self, name: str, value: Any) -> None:
        """Declara sem checagens (uso interno: builtins e parâmetros)."""
        self.values[name] = value

    def get(self, name: str, node: Node | None = None, filename: str = "<programa>") -> Any:
        env: Environment | None = self
        while env is not None:
            if name in env.values:
                return env.values[name]
            env = env.parent
        raise _runtime_error(
            filename, node, f"variável '{name}' não foi definida (use 'let {name} = ...')"
        )

    def assign(self, name: str, value: Any, node: Node | None = None, filename: str = "<programa>") -> None:
        env: Environment | None = self
        while env is not None:
            if name in env.values:
                env.values[name] = value
                return
            env = env.parent
        if name in BUILTIN_NAMES:
            raise _runtime_error(
                filename, node, f"não é possível atribuir a '{name}': é uma função embutida"
            )
        raise _runtime_error(
            filename,
            node,
            f"não é possível atribuir a '{name}': a variável não foi declarada (use 'let {name} = ...')",
        )


def _runtime_error(filename: str | None, node: Node | None, message: str) -> OblivionRuntimeError:
    """Cria um erro de execução apontando o nodo (quando houver)."""
    line = node.line if node is not None else 0
    column = node.column if node is not None else 0
    # filename é preenchido pelo chamador quando disponível; aqui usamos o padrão.
    return OblivionRuntimeError(message, filename=filename or "<programa>", line=line, column=column)


# ----------------------------------------------------------------------
# Formatação de valores
# ----------------------------------------------------------------------
def type_name(value: Any) -> str:
    """Nome do tipo de um valor, para mensagens de erro em português."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "lista"
    if isinstance(value, dict):
        return "mapa"
    if isinstance(value, (FunctionValue, BuiltinFunction)):
        return "função"
    return "valor desconhecido"


def _format_key(key: str) -> str:
    """Chave de mapa sem aspas se for um nome válido; senão entre aspas."""
    if key and (key[0].isalpha() or key[0] == "_") and all(
        ch.isalnum() or ch == "_" for ch in key
    ):
        return key
    return '"' + key + '"'


def _format_nested(value: Any, depth: int) -> str:
    """Formata valores dentro de coleções (textos aparecem entre aspas)."""
    if depth >= _MAX_FORMAT_DEPTH:
        return "..."
    if isinstance(value, str):
        return '"' + value + '"'
    if isinstance(value, list):
        return "[" + ", ".join(_format_nested(item, depth + 1) for item in value) + "]"
    if isinstance(value, dict):
        entries = (
            f"{_format_key(key)}: {_format_nested(item, depth + 1)}"
            for key, item in value.items()
        )
        return "{" + ", ".join(entries) + "}"
    return format_value(value)


def format_value(value: Any) -> str:
    """Como um valor aparece no ``print`` (``True``/``False`` com maiúscula)."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, dict)):
        return _format_nested(value, 0)
    if isinstance(value, (int, float, FunctionValue, BuiltinFunction)):
        return str(value)
    return str(value)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _truthy(value: Any) -> bool:
    """Verdade: tudo é verdadeiro, exceto ``false``, ``null``, ``0``, ``""`` e coleções vazias."""
    if value is None or isinstance(value, bool):
        return bool(value)
    if _is_number(value):
        return value != 0
    if isinstance(value, str):
        return value != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _values_equal(a: Any, b: Any) -> bool:
    """``==`` estrito quanto a tipos, profundo para listas e mapas."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if _is_number(a) and _is_number(b):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if a is None and b is None:
        return True
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            _values_equal(x, y) for x, y in zip(a, b)
        )
    if isinstance(a, dict) and isinstance(b, dict):
        if len(a) != len(b):
            return False
        for key, value in a.items():
            if key not in b or not _values_equal(value, b[key]):
                return False
        return True
    if isinstance(a, (FunctionValue, BuiltinFunction)) and isinstance(b, (FunctionValue, BuiltinFunction)):
        return a is b
    return False


class _Return(Exception):
    """Sinal interno usado pelo ``return`` para sair da função."""

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value


class _Break(Exception):
    """Sinal interno do ``break`` (pegue apenas no laço mais interno)."""


class _Continue(Exception):
    """Sinal interno do ``continue`` (pegue apenas no laço mais interno)."""


# ----------------------------------------------------------------------
# Interpretador
# ----------------------------------------------------------------------
class Interpreter:
    """Executa a AST de um programa Oblivion."""

    def __init__(
        self,
        *,
        output: Callable[[str], None] | None = None,
        max_steps: int = DEFAULT_MAX_STEPS,
        filename: str = "<programa>",
    ) -> None:
        self.filename = filename
        self.max_steps = max_steps
        self.steps = 0  # passos executados até agora (zerado a cada rodada no REPL)
        self._output: Callable[[str], None] = print if output is None else output
        self.globals = Environment()
        self.env = self.globals
        self._install_builtins()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def run(self, program: list[Node]) -> None:
        """Executa uma lista de instruções no escopo global."""
        try:
            for statement in program:
                self._execute(statement)
        except (_Break, _Continue):
            # O parser já recusa isso; defesa extra para não vazar traceback.
            raise self._error(None, "'break'/'continue' fora de um laço") from None

    # ------------------------------------------------------------------
    # Proteções de execução
    # ------------------------------------------------------------------
    def _tick(self, node: Node) -> None:
        """Conta um passo de execução e aplica o limite configurado."""
        self.steps += 1
        if self.steps > self.max_steps:
            raise self._error(
                node,
                f"limite de {self.max_steps} passos de execução atingido — "
                "possível laço infinito (use --max-steps para aumentar o limite)",
            )

    def _error(self, node: Node | None, message: str) -> OblivionRuntimeError:
        line = node.line if node is not None else 0
        column = node.column if node is not None else 0
        return OblivionRuntimeError(
            message, filename=self.filename, line=line, column=column
        )

    # ------------------------------------------------------------------
    # Instruções
    # ------------------------------------------------------------------
    def _execute(self, node: Node) -> None:
        self._tick(node)
        match node:
            case LetStatement(name=name, initializer=initializer):
                value = self._evaluate(initializer)
                self.env.declare(name, value, node, self.filename)
            case AssignStatement(name=name, value=value_expr):
                value = self._evaluate(value_expr)
                self.env.assign(name, value, node, self.filename)
            case ExpressionStatement(expression=expression):
                self._evaluate(expression)
            case IfStatement(condition=condition, then_block=then, else_branch=otherwise):
                if _truthy(self._evaluate(condition)):
                    self._execute(then)
                elif otherwise is not None:
                    self._execute(otherwise)
            case WhileStatement(condition=condition, body=body):
                while _truthy(self._evaluate(condition)):
                    try:
                        self._execute(body)
                    except _Continue:
                        continue
                    except _Break:
                        break
            case ForStatement(name=name, iterable=iterable, body=body):
                self._for_loop(name, iterable, body, node)
            case BreakStatement():
                raise _Break()
            case ContinueStatement():
                raise _Continue()
            case IndexAssign(target=target, value=value_expr):
                container = self._evaluate(target.target)
                key = self._evaluate(target.index)
                value = self._evaluate(value_expr)
                self._index_set(container, key, value, node)
            case MemberAssign(target=target, value=value_expr):
                container = self._evaluate(target.target)
                value = self._evaluate(value_expr)
                self._member_set(container, target.name, value, node)
            case BlockStatement(statements=statements):
                self._execute_block(statements, Environment(self.env))
            case FunctionDeclaration(name=name, params=params, body=body):
                function = FunctionValue(name, params, body, self.env)
                self.env.declare(name, function, node, self.filename)
            case ReturnStatement(value=value_expr):
                value = self._evaluate(value_expr) if value_expr is not None else None
                raise _Return(value)
            case _:
                raise self._error(node, f"instrução desconhecida na AST: {type(node).__name__}")

    def _execute_block(self, statements: list[Node], env: Environment) -> None:
        """Executa um bloco com ``env`` como escopo atual (sempre restaura)."""
        previous = self.env
        self.env = env
        try:
            for statement in statements:
                self._execute(statement)
        finally:
            self.env = previous

    def _for_loop(self, name: str, iterable: Node, body: BlockStatement, node: Node) -> None:
        """Executa ``for nome in colecao { ... }`` (lista, mapa ou texto)."""
        items = self._iter_items(self._evaluate(iterable), node)
        # A variável do laço vive num escopo filho que só existe durante o for.
        loop_env = Environment(self.env)
        loop_env.declare_raw(name, None)
        for item in items:
            self._tick(node)  # cada iteração conta como passo de execução
            loop_env.values[name] = item
            try:
                self._execute_block(body.statements, Environment(loop_env))
            except _Continue:
                continue
            except _Break:
                break

    def _iter_items(self, value: Any, node: Node) -> list[Any]:
        """Itens percorridos por um ``for``: lista → elementos, mapa → chaves,
        texto → caracteres (é feita uma cópia, então alterar a coleção durante
        o laço é seguro)."""
        if isinstance(value, list):
            return list(value)
        if isinstance(value, dict):
            return list(value.keys())
        if isinstance(value, str):
            return list(value)
        raise self._error(
            node,
            f"'for' só percorre listas, mapas (chaves) e textos "
            f"(recebeu {type_name(value)})",
        )

    # ------------------------------------------------------------------
    # Expressões
    # ------------------------------------------------------------------
    def _evaluate(self, node: Node) -> Any:
        self._tick(node)
        match node:
            case NumberLiteral(value=value):
                return value
            case StringLiteral(value=value):
                return value
            case BooleanLiteral(value=value):
                return value
            case NullLiteral():
                return None
            case Variable(name=name):
                return self.env.get(name, node, self.filename)
            case Grouping(expression=expression):
                return self._evaluate(expression)
            case Unary(operator=operator, operand=operand):
                return self._unary(operator, operand, node)
            case Logical(left=left, operator=operator, right=right):
                return self._logical(left, operator, right, node)
            case Binary(left=left, operator=operator, right=right):
                return self._binary(left, operator, right, node)
            case Call(callee=callee, arguments=arguments):
                function = self._evaluate(callee)
                args = [self._evaluate(argument) for argument in arguments]
                return self._call(function, args, node)
            case ListLiteral(elements=elements):
                return [self._evaluate(element) for element in elements]
            case MapLiteral(pairs=pairs):
                return {
                    key: self._evaluate(expression) for key, expression in pairs.items()
                }
            case Index(target=target, index=index):
                return self._index_get(
                    self._evaluate(target), self._evaluate(index), node
                )
            case Member(target=target, name=name):
                return self._member_get(self._evaluate(target), name, node)
            case _:
                raise self._error(node, f"expressão desconhecida na AST: {type(node).__name__}")

    def _unary(self, operator: str, operand: Node, node: Node) -> Any:
        value = self._evaluate(operand)
        if operator == "-":
            if not _is_number(value):
                raise self._error(
                    node, f"operador '-' não aceita {type_name(value)} (só números)"
                )
            return -value
        # 'not' funciona com qualquer valor (usa a regra de verdade).
        return not _truthy(value)

    def _logical(self, left: Node, operator: str, right: Node, node: Node) -> bool:
        """``and``/``or`` curto-circuitam e sempre devolvem true/false."""
        left_value = self._evaluate(left)
        if operator == "or":
            if _truthy(left_value):
                return True
            return _truthy(self._evaluate(right))
        # and
        if not _truthy(left_value):
            return False
        return _truthy(self._evaluate(right))

    def _binary(self, left: Node, operator: str, right: Node, node: Node) -> Any:
        left_value = self._evaluate(left)
        right_value = self._evaluate(right)

        if operator == "==":
            return _values_equal(left_value, right_value)
        if operator == "!=":
            return not _values_equal(left_value, right_value)
        if operator in ("<", "<=", ">", ">="):
            return self._compare(operator, left_value, right_value, node)

        if operator == "+":
            if _is_number(left_value) and _is_number(right_value):
                return left_value + right_value
            if isinstance(left_value, str) and isinstance(right_value, str):
                result = left_value + right_value
                if len(result) > MAX_STRING_LENGTH:
                    raise self._error(
                        node,
                        f"texto muito grande: {len(result)} caracteres (limite {MAX_STRING_LENGTH})",
                    )
                return result
            if isinstance(left_value, list) and isinstance(right_value, list):
                if len(left_value) + len(right_value) > MAX_COLLECTION_LENGTH:
                    raise self._error(
                        node,
                        f"lista muito grande: limite de {MAX_COLLECTION_LENGTH} elementos",
                    )
                return left_value + right_value
            raise self._error(
                node,
                f"operador '+' não aceita {type_name(left_value)} e {type_name(right_value)} "
                "(só número + número, texto + texto ou lista + lista)",
            )

        # Operadores aritméticos: só números.
        if not (_is_number(left_value) and _is_number(right_value)):
            raise self._error(
                node,
                f"operador '{operator}' não aceita {type_name(left_value)} e {type_name(right_value)} (só números)",
            )
        if operator == "-":
            return left_value - right_value
        if operator == "*":
            return left_value * right_value
        if right_value == 0:
            raise self._error(node, f"divisão por zero em '{operator}'")
        if operator == "/":
            return left_value / right_value
        if operator == "//":
            return left_value // right_value
        # operator == "%"
        return left_value % right_value

    def _compare(self, operator: str, a: Any, b: Any, node: Node) -> bool:
        if _is_number(a) and _is_number(b):
            pass
        elif isinstance(a, str) and isinstance(b, str):
            pass
        else:
            raise self._error(
                node,
                f"não é possível comparar {type_name(a)} com {type_name(b)} usando '{operator}'",
            )
        if operator == "<":
            return a < b
        if operator == "<=":
            return a <= b
        if operator == ">":
            return a > b
        return a >= b

    # ------------------------------------------------------------------
    # Indexação (listas/mapas) e propriedades (mapas)
    # ------------------------------------------------------------------
    @staticmethod
    def _is_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _list_position(self, key: Any, length: int, node: Node) -> int:
        """Converte um índice (aceita negativo, como Python) ou falha."""
        if not self._is_int(key):
            raise self._error(
                node,
                f"índice de lista precisa ser um número inteiro (recebeu {type_name(key)})",
            )
        position = key + length if key < 0 else key
        if position < 0 or position >= length:
            raise self._error(
                node,
                f"índice {key} fora dos limites: a lista tem {length} elemento(s)",
            )
        return position

    def _index_get(self, container: Any, key: Any, node: Node) -> Any:
        if isinstance(container, list):
            return container[self._list_position(key, len(container), node)]
        if isinstance(container, dict):
            if not isinstance(key, str):
                raise self._error(
                    node,
                    f"chave de mapa precisa ser um texto (recebeu {type_name(key)})",
                )
            return container.get(key)  # chave ausente → null
        raise self._error(
            node,
            f"só listas e mapas podem ser indexados com [...] (recebeu {type_name(container)})",
        )

    def _index_set(self, container: Any, key: Any, value: Any, node: Node) -> None:
        if isinstance(container, list):
            container[self._list_position(key, len(container), node)] = value
            return
        if isinstance(container, dict):
            if not isinstance(key, str):
                raise self._error(
                    node,
                    f"chave de mapa precisa ser um texto (recebeu {type_name(key)})",
                )
            if key not in container and len(container) >= MAX_COLLECTION_LENGTH:
                raise self._error(
                    node, f"mapa cheio: limite de {MAX_COLLECTION_LENGTH} chaves"
                )
            container[key] = value  # cria ou atualiza
            return
        raise self._error(
            node,
            f"só listas e mapas aceitam 'alvo[índice] = valor' "
            f"(recebeu {type_name(container)})",
        )

    def _member_get(self, container: Any, name: str, node: Node) -> Any:
        if isinstance(container, dict):
            return container.get(name)  # propriedade ausente → null
        raise self._error(
            node,
            f"só mapas têm propriedades com '.' (recebeu {type_name(container)})",
        )

    def _member_set(self, container: Any, name: str, value: Any, node: Node) -> None:
        if isinstance(container, dict):
            if name not in container and len(container) >= MAX_COLLECTION_LENGTH:
                raise self._error(
                    node, f"mapa cheio: limite de {MAX_COLLECTION_LENGTH} chaves"
                )
            container[name] = value  # cria ou atualiza
            return
        raise self._error(
            node,
            f"só mapas aceitam 'mapa.propriedade = valor' "
            f"(recebeu {type_name(container)})",
        )

    def _call(self, function: Any, args: list[Any], node: Node) -> Any:
        if isinstance(function, BuiltinFunction):
            count = len(args)
            if count < function.min_args or (
                function.max_args is not None and count > function.max_args
            ):
                raise self._error(node, self._arity_message(function.name, function.min_args, function.max_args, count))
            return function.implementation(args, node)
        if isinstance(function, FunctionValue):
            expected = len(function.params)
            if len(args) != expected:
                raise self._error(
                    node,
                    f"função '{function.name}' espera {expected} argumento(s), mas recebeu {len(args)}",
                )
            call_env = Environment(function.declaration_env)
            for param, value in zip(function.params, args):
                call_env.declare_raw(param, value)
            try:
                self._execute_block(function.body.statements, call_env)
            except _Return as return_signal:
                return return_signal.value
            return None  # função sem 'return' devolve null
        raise self._error(node, f"{type_name(function)} não é chamável")

    @staticmethod
    def _arity_message(name: str, minimum: int, maximum: int | None, got: int) -> str:
        if maximum is None:
            return f"função '{name}' espera pelo menos {minimum} argumento(s), mas recebeu {got}"
        if minimum == maximum:
            return f"função '{name}' espera {minimum} argumento(s), mas recebeu {got}"
        return f"função '{name}' espera entre {minimum} e {maximum} argumentos, mas recebeu {got}"

    # ------------------------------------------------------------------
    # Funções embutidas
    # ------------------------------------------------------------------
    def _install_builtins(self) -> None:
        self.globals.declare_raw(
            "print", BuiltinFunction("print", 0, None, self._builtin_print)
        )
        self.globals.declare_raw("len", BuiltinFunction("len", 1, 1, self._builtin_len))
        self.globals.declare_raw("push", BuiltinFunction("push", 2, 2, self._builtin_push))

    def _builtin_print(self, args: list[Any], node: Node) -> None:
        self._output(" ".join(format_value(value) for value in args))
        return None

    def _builtin_len(self, args: list[Any], node: Node) -> int:
        value = args[0]
        if isinstance(value, (str, list, dict)):
            return len(value)
        raise self._error(
            node,
            f"função 'len' espera uma string, lista ou mapa, mas recebeu {type_name(value)}",
        )

    def _builtin_push(self, args: list[Any], node: Node) -> None:
        collection, value = args
        if not isinstance(collection, list):
            raise self._error(
                node,
                f"função 'push' espera uma lista, mas recebeu {type_name(collection)}",
            )
        if len(collection) >= MAX_COLLECTION_LENGTH:
            raise self._error(
                node, f"lista cheia: limite de {MAX_COLLECTION_LENGTH} elementos"
            )
        collection.append(value)
        return None

"""Testes do parser (etapa 2): precedência, estrutura da AST e sintaxe inválida."""
from __future__ import annotations

import unittest

from oblivion import parse_source
from oblivion.ast_nodes import (
    AssignStatement,
    Binary,
    BooleanLiteral,
    Call,
    ExpressionStatement,
    FunctionDeclaration,
    Grouping,
    IfStatement,
    LetStatement,
    Logical,
    NumberLiteral,
    ReturnStatement,
    StringLiteral,
    Unary,
    Variable,
    WhileStatement,
)
from oblivion.errors import OblivionSyntaxError


class PrecedenceTests(unittest.TestCase):
    def test_multiplication_binds_tighter_than_addition(self):
        [statement] = parse_source("let r = 1 + 2 * 3")
        self.assertIsInstance(statement, LetStatement)
        root = statement.initializer
        self.assertIsInstance(root, Binary)
        self.assertEqual(root.operator, "+")
        self.assertIsInstance(root.left, NumberLiteral)
        self.assertIsInstance(root.right, Binary)
        self.assertEqual(root.right.operator, "*")

    def test_parentheses_group_expressions(self):
        [statement] = parse_source("let r = (1 + 2) * 3")
        root = statement.initializer
        self.assertIsInstance(root, Binary)
        self.assertEqual(root.operator, "*")
        self.assertIsInstance(root.left, Grouping)
        self.assertIsInstance(root.left.expression, Binary)

    def test_unary_minus_binds_tighter_than_multiplication(self):
        [statement] = parse_source("let r = -x * y")
        root = statement.initializer
        self.assertIsInstance(root, Binary)
        self.assertEqual(root.operator, "*")
        self.assertIsInstance(root.left, Unary)

    def test_comparison_binds_tighter_than_logical_and(self):
        [statement] = parse_source("let ok = x < 1 and y > 2")
        root = statement.initializer
        self.assertIsInstance(root, Logical)
        self.assertEqual(root.operator, "and")
        self.assertIsInstance(root.left, Binary)
        self.assertEqual(root.left.operator, "<")

    def test_not_binds_looser_than_comparison(self):
        # not a == b  significa  not (a == b)
        [statement] = parse_source("let r = not a == b")
        root = statement.initializer
        self.assertIsInstance(root, Unary)
        self.assertEqual(root.operator, "not")
        self.assertIsInstance(root.operand, Binary)
        self.assertEqual(root.operand.operator, "==")

    def test_or_binds_looser_than_and(self):
        [statement] = parse_source("let r = a or b and c")
        root = statement.initializer
        self.assertIsInstance(root, Logical)
        self.assertEqual(root.operator, "or")
        self.assertIsInstance(root.right, Logical)
        self.assertEqual(root.right.operator, "and")

    def test_left_associativity_of_subtraction(self):
        [statement] = parse_source("let r = 10 - 4 - 3")
        root = statement.initializer
        self.assertEqual(root.operator, "-")
        self.assertIsInstance(root.left, Binary)  # ((10 - 4) - 3)

    def test_chained_call_and_arguments(self):
        [statement] = parse_source('print("a", 1 + 2, f(x))')
        self.assertIsInstance(statement, ExpressionStatement)
        call = statement.expression
        self.assertIsInstance(call, Call)
        self.assertIsInstance(call.callee, Variable)
        self.assertEqual(len(call.arguments), 3)
        self.assertIsInstance(call.arguments[1], Binary)


class StatementShapeTests(unittest.TestCase):
    def test_let_and_literal_types(self):
        statements = parse_source('let n = 1\nlet s = "oi"\nlet b = true')
        self.assertIsInstance(statements[0], LetStatement)
        self.assertIsInstance(statements[0].initializer, NumberLiteral)
        self.assertIsInstance(statements[1].initializer, StringLiteral)
        self.assertIsInstance(statements[2].initializer, BooleanLiteral)

    def test_assignment_statement(self):
        [statement] = parse_source("x = 1")
        self.assertIsInstance(statement, AssignStatement)
        self.assertEqual(statement.name, "x")

    def test_equality_is_not_assignment(self):
        [statement] = parse_source("x == 1")
        self.assertIsInstance(statement, ExpressionStatement)

    def test_if_with_else_block(self):
        statements = parse_source('if x {\n    print(1)\n} else {\n    print(2)\n}')
        [if_statement] = statements
        self.assertIsInstance(if_statement, IfStatement)
        self.assertIsNotNone(if_statement.else_branch)
        self.assertEqual(len(if_statement.then_block.statements), 1)

    def test_else_if_chain(self):
        source = "if a {\n    1\n} else if b {\n    2\n} else {\n    3\n}"
        [if_statement] = parse_source(source)
        self.assertIsInstance(if_statement.else_branch, IfStatement)
        self.assertIsNotNone(if_statement.else_branch.else_branch)

    def test_while_with_block(self):
        source = "while x < 10 {\n    x = x + 1\n}"
        [while_statement] = parse_source(source)
        self.assertIsInstance(while_statement, WhileStatement)
        self.assertEqual(len(while_statement.body.statements), 1)

    def test_function_declaration(self):
        source = "fun soma(a, b) {\n    return a + b\n}"
        [function] = parse_source(source)
        self.assertIsInstance(function, FunctionDeclaration)
        self.assertEqual(function.name, "soma")
        self.assertEqual(function.params, ["a", "b"])
        self.assertIsInstance(function.body.statements[0], ReturnStatement)

    def test_return_without_value(self):
        source = "fun f() {\n    return\n}"
        [function] = parse_source(source)
        self.assertIsInstance(function.body.statements[0], ReturnStatement)
        self.assertIsNone(function.body.statements[0].value)

    def test_multiline_expression_inside_parentheses(self):
        source = "let r = (1 +\n         2)"
        [statement] = parse_source(source)
        self.assertIsInstance(statement.initializer, Grouping)


class SyntaxErrorTests(unittest.TestCase):
    def assertSyntaxError(self, source: str, fragment: str) -> None:
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source(source, filename="erro.obl")
        self.assertIn(
            fragment,
            ctx.exception.message,
            f"esperava {fragment!r} na mensagem: {ctx.exception.message}",
        )
        self.assertEqual(ctx.exception.filename, "erro.obl")

    def test_missing_closing_paren(self):
        self.assertSyntaxError("print((1 + 2", "')'")

    def test_missing_equals_in_let(self):
        self.assertSyntaxError("let x 5", "'='")

    def test_let_without_name(self):
        self.assertSyntaxError("let = 5", "nome de variável")

    def test_unclosed_block(self):
        self.assertSyntaxError("if x {\n    print(1)\n", "'}'")

    def test_missing_opening_brace_in_block(self):
        self.assertSyntaxError("if x print(1)", "'{'")

    def test_missing_expression(self):
        self.assertSyntaxError("let x = ", "esperava uma expressão")

    def test_two_statements_on_one_line(self):
        self.assertSyntaxError("let x = 1 let y = 2", "fim da linha")

    def test_return_outside_function(self):
        self.assertSyntaxError("return 1", "dentro de uma função")

    def test_else_without_if(self):
        self.assertSyntaxError("let x = 1\nelse {\n}", "'if'")

    def test_stray_closing_brace(self):
        self.assertSyntaxError("let x = 1\n}", "'}'")

    def test_bare_block_is_rejected(self):
        self.assertSyntaxError("{\n    print(1)\n}", "'{' inesperado")

    def test_duplicate_parameters(self):
        self.assertSyntaxError("fun f(a, a) {\n}", "parâmetro repetido")

    def test_syntax_error_reports_line_and_column(self):
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source("let a = 1\nlet b = =", filename="x.obl")
        error = ctx.exception
        self.assertEqual((error.line, error.column), (2, 9))
        self.assertIn("erro de sintaxe", str(error))
        self.assertIn("x.obl:2:9:", str(error))

    def test_too_many_arguments(self):
        source = "f(" + ", ".join(str(i) for i in range(256)) + ")"
        self.assertSyntaxError(source, "255 argumentos")


if __name__ == "__main__":
    unittest.main()

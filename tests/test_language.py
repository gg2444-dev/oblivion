"""Testes de comportamento da linguagem (lexer + parser + interpretador juntos)."""
from __future__ import annotations

import unittest

from oblivion import run_source
from oblivion.errors import OblivionRuntimeError
from oblivion.interpreter import DEFAULT_MAX_STEPS

HELLO_SOURCE = """\
# My first Oblivion program
let name = "Alex"
let age = 16
let result = 10 + 5 * 2
print("Hello, " + name)
print("Your age:", age)
print("Calculation:", result)
print("Are you a teenager?", age >= 13 and age <= 19)
"""

HELLO_EXPECTED = """\
Hello, Alex
Your age: 16
Calculation: 20
Are you a teenager? True"""


def run(source: str, max_steps: int = DEFAULT_MAX_STEPS, filename: str = "prog.obl") -> str:
    """Executa código e devolve tudo que o ``print`` escreveu (uma string)."""
    lines: list[str] = []
    run_source(source, filename=filename, output=lines.append, max_steps=max_steps)
    return "\n".join(lines)


class HelloWorldTests(unittest.TestCase):
    def test_required_example_exact_output(self):
        self.assertEqual(run(HELLO_SOURCE), HELLO_EXPECTED)

    def test_print_with_zero_arguments(self):
        self.assertEqual(run("print()"), "")

    def test_print_with_multiple_arguments_uses_spaces(self):
        self.assertEqual(run('print("a", 1, true)'), "a 1 True")


class ArithmeticTests(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(run("print(10 + 5 * 2)"), "20")
        self.assertEqual(run("print(2 + 3 * 4)"), "14")
        self.assertEqual(run("print(20 - 6 / 3)"), "18.0")  # '/' vira decimal

    def test_parentheses_change_precedence(self):
        self.assertEqual(run("print((10 + 5) * 2)"), "30")
        self.assertEqual(run("print(2 * (3 + 4))"), "14")

    def test_floor_division_modulo_and_true_division(self):
        self.assertEqual(run("print(10 / 4)"), "2.5")
        self.assertEqual(run("print(10 // 3)"), "3")
        self.assertEqual(run("print(-7 // 2)"), "-4")
        self.assertEqual(run("print(10 % 3)"), "1")

    def test_unary_minus(self):
        self.assertEqual(run("print(-3 + 5)"), "2")
        self.assertEqual(run("print(-(2 + 3))"), "-5")

    def test_left_associativity(self):
        self.assertEqual(run("print(10 - 4 - 3)"), "3")
        self.assertEqual(run("print(100 / 10 / 2)"), "5.0")

    def test_division_by_zero_is_a_runtime_error(self):
        for source in ("print(1 / 0)", "print(1 // 0)", "print(1 % 0)"):
            with self.subTest(source=source):
                with self.assertRaises(OblivionRuntimeError) as ctx:
                    run(source)
                self.assertIn("divisão por zero", ctx.exception.message)


class StringTests(unittest.TestCase):
    def test_concatenation_and_variables(self):
        self.assertEqual(run('let s = "ob" + "lvi" + "on"\nprint(s)'), "oblvi" + "on")

    def test_len_builtin(self):
        self.assertEqual(run('print(len("abc"))'), "3")
        self.assertEqual(run('print(len(""))'), "0")

    def test_escapes_are_decoded(self):
        self.assertEqual(run('print("a\\nb")'), "a\nb")

    def test_plus_rejects_mixed_types(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run('print("idade: " + 16)')
        self.assertIn("'+'", ctx.exception.message)

    def test_len_rejects_numbers(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("print(len(42))")
        self.assertIn("string", ctx.exception.message)


class VariableTests(unittest.TestCase):
    def test_declaration_and_print(self):
        self.assertEqual(run('let x = 7\nprint(x)'), "7")

    def test_reassignment_is_allowed(self):
        source = "let x = 1\nx = x + 1\nx = x * 10\nprint(x)"
        self.assertEqual(run(source), "20")

    def test_redeclaration_in_same_scope_is_an_error(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("let x = 1\nlet x = 2")
        self.assertIn("já foi declarada", ctx.exception.message)

    def test_undefined_variable(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("print(naoExiste)", filename="meu.obl")
        error = ctx.exception
        self.assertIn("não foi definida", error.message)
        self.assertIn("naoExiste", error.message)
        self.assertEqual((error.filename, error.line, error.column), ("meu.obl", 1, 7))

    def test_assignment_without_declaration_is_an_error(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("x = 5")
        self.assertIn("let x", ctx.exception.message)

    def test_builtin_names_cannot_be_redeclared(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("let print = 1")
        self.assertIn("embutida", ctx.exception.message)


class BooleanTests(unittest.TestCase):
    def test_literals_print_python_style(self):
        self.assertEqual(run("print(true, false, null)"), "True False null")

    def test_comparisons(self):
        source = """\
print(1 < 2, 2 <= 2, 3 > 4, 4 >= 4)
print(1 == 1, 1 != 2, 1 == 1.0)
print("a" < "b", "ab" == "ab")
print(true == true, true != false)
print(null == null)
"""
        self.assertEqual(
            run(source),
            "True True False True\nTrue True True\nTrue True\nTrue True\nTrue",
        )

    def test_boolean_is_not_a_number(self):
        self.assertEqual(run("print(true == 1)"), "False")

    def test_logical_operators_return_booleans(self):
        source = """\
print(true and false, true or false, not true)
print(1 and 2, 0 or "", not 0)
"""
        self.assertEqual(run(source), "False True False\nTrue False True")

    def test_and_short_circuits(self):
        self.assertEqual(run('false and print("não deve aparecer")'), "")

    def test_or_short_circuits(self):
        self.assertEqual(run('true or print("não deve aparecer")'), "")


class ControlFlowTests(unittest.TestCase):
    def test_if_branch_taken(self):
        source = 'let n = 10\nif n > 5 {\n    print("grande")\n} else {\n    print("pequeno")\n}'
        self.assertEqual(run(source), "grande")

    def test_else_branch_taken(self):
        source = 'let n = 1\nif n > 5 {\n    print("grande")\n} else {\n    print("pequeno")\n}'
        self.assertEqual(run(source), "pequeno")

    def test_else_if_chain(self):
        source = """\
let n = 7
if n < 5 {
    print("menor")
} else if n < 10 {
    print("meio")
} else {
    print("maior")
}
"""
        self.assertEqual(run(source), "meio")

    def test_nested_conditionals(self):
        source = """\
let a = 2
let b = 3
if a < b {
    if b == 3 {
        print("sim")
    }
} else {
    print("nao")
}
"""
        self.assertEqual(run(source), "sim")

    def test_falsy_values_in_conditions(self):
        source = """\
if 0 {
    print("verdadeiro")
} else {
    print("falso")
}
if "" {
    print("v1")
} else {
    print("v0")
}
if null {
    print("n1")
} else {
    print("n0")
}
"""
        self.assertEqual(run(source), "falso\nv0\nn0")

    def test_while_loop_accumulates(self):
        source = """\
let i = 1
let soma = 0
while i <= 10 {
    soma = soma + i
    i = i + 1
}
print(soma)
"""
        self.assertEqual(run(source), "55")

    def test_while_with_complex_condition(self):
        source = """\
let texto = "inicio"
while texto != "fim" {
    texto = texto + "x"
    if len(texto) > 6 {
        texto = "fim"
    }
}
print(texto)
"""
        self.assertEqual(run(source), "fim")

    def test_infinite_loop_hits_step_limit(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("while true {\n}", max_steps=500)
        self.assertIn("limite de 500 passos", ctx.exception.message)
        self.assertIn("laço infinito", ctx.exception.message)

    def test_step_limit_reports_position(self):
        source = "let i = 0\nwhile true {\n    i = i + 1\n}"
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run(source, max_steps=100)
        # O limite estoura dentro do laço: condição/linha do while ou o corpo.
        self.assertIn(ctx.exception.line, (2, 3))
        self.assertGreater(ctx.exception.column, 0)

    def test_default_limit_allows_normal_loops(self):
        source = "let i = 0\nwhile i < 1000 {\n    i = i + 1\n}\nprint(i)"
        self.assertEqual(run(source), "1000")


class ErrorReportingTests(unittest.TestCase):
    def test_runtime_error_format(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run('let a = 1\nprint(a + "x")', filename="calc.obl")
        text = str(ctx.exception)
        self.assertTrue(text.startswith("calc.obl:2:9: erro em tempo de execução: "))
        self.assertIn("'+'", text)

    def test_type_error_in_comparison(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run('print(1 < "a")')
        self.assertIn("comparar", ctx.exception.message)

    def test_cannot_call_non_function(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("let x = 1\nx()")
        self.assertIn("não é chamável", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()

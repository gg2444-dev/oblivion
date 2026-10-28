"""Testes de funções: declaração, chamada, retorno, escopo, recursão e closures."""
from __future__ import annotations

import unittest

from oblivion import run_source
from oblivion.errors import OblivionRuntimeError, OblivionSyntaxError

from .test_language import run


class FunctionTests(unittest.TestCase):
    def test_call_and_return_value(self):
        source = """\
fun soma(a, b) {
    return a + b
}
print(soma(2, 3))
"""
        self.assertEqual(run(source), "5")

    def test_function_without_return_returns_null(self):
        source = "fun f() {\n    print(\"oi\")\n}\nf()"
        self.assertEqual(run(source), "oi")

    def test_return_bare_prints_null(self):
        source = "fun f() {\n    return\n}\nprint(f())"
        self.assertEqual(run(source), "null")

    def test_function_value_prints_as_fun(self):
        source = "fun f() {\n    return 1\n}\nprint(f)"
        self.assertEqual(run(source), "<fun f>")

    def test_arguments_are_evaluated_in_order(self):
        source = """\
fun escolhe(a, b) {
    return a
}
let x = 1
print(escolhe(x, 2))
"""
        self.assertEqual(run(source), "1")

    def test_locals_do_not_leak_to_global_scope(self):
        source = """\
fun usaLocal() {
    let interno = 42
    return interno
}
print(usaLocal())
print(interno)
"""
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run_source(
                source,
                filename="prog.obl",
                output=lambda _line: None,
            )
        self.assertIn("interno", ctx.exception.message)

    def test_parameters_are_local_to_each_call(self):
        source = """\
fun dobra(x) {
    return x * 2
}
let x = 100
print(dobra(5))
print(x)
"""
        self.assertEqual(run(source), "10\n100")

    def test_recursion_fibonacci(self):
        source = """\
fun fib(n) {
    if n < 2 {
        return n
    }
    return fib(n - 1) + fib(n - 2)
}
print(fib(10))
"""
        self.assertEqual(run(source), "55")

    def test_recursion_factorial(self):
        source = """\
fun fat(n) {
    if n <= 1 {
        return 1
    }
    return n * fat(n - 1)
}
print(fat(6))
"""
        self.assertEqual(run(source), "720")

    def test_wrong_number_of_arguments(self):
        source = "fun f(a, b) {\n    return a\n}\nf(1)"
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run(source)
        self.assertIn("espera 2 argumento(s)", ctx.exception.message)

    def test_closure_keeps_state_between_calls(self):
        source = """\
fun novoContador() {
    let n = 0
    fun incrementar() {
        n = n + 1
        return n
    }
    return incrementar
}
let c = novoContador()
print(c())
print(c())
print(c())
"""
        self.assertEqual(run(source), "1\n2\n3")

    def test_higher_order_function(self):
        source = """\
fun aplicar(f, valor) {
    return f(valor)
}
fun dobra(x) {
    return x * 2
}
print(aplicar(dobra, 21))
"""
        self.assertEqual(run(source), "42")

    def test_function_redeclared_in_same_scope_fails(self):
        source = "fun f() {\n    return 1\n}\nfun f() {\n    return 2\n}"
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run(source)
        self.assertIn("já foi declarada", ctx.exception.message)

    def test_deep_recursion_gives_friendly_error(self):
        source = "fun f(n) {\n    return f(n + 1)\n}\nf(0)"
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run(source, max_steps=100_000_000)
        self.assertIn("recursão", ctx.exception.message)

    def test_syntax_error_still_reports_return_outside_function(self):
        with self.assertRaises(OblivionSyntaxError):
            run_source("fun f() {\n}\nreturn 1", filename="p.obl", output=lambda _l: None)


if __name__ == "__main__":
    unittest.main()

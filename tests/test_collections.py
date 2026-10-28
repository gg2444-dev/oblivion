"""Testes do milestone 1: listas, mapas, indexação, propriedades, for, break/continue."""
from __future__ import annotations

import unittest

from oblivion import parse_source, run_source
from oblivion.ast_nodes import (
    BreakStatement,
    ContinueStatement,
    ForStatement,
    Index,
    IndexAssign,
    ListLiteral,
    MapLiteral,
    Member,
    MemberAssign,
)
from oblivion.errors import OblivionRuntimeError, OblivionSyntaxError

from .test_language import run


class ListTests(unittest.TestCase):
    def test_list_literal_prints(self):
        self.assertEqual(run('print([1, "dois", null, true])'), '[1, "dois", null, True]')

    def test_empty_list(self):
        self.assertEqual(run("let vazio = []\nprint(vazio, len(vazio))"), "[] 0")

    def test_multiline_list_literal(self):
        source = "let xs = [\n    1,\n    2,\n]\nprint(len(xs))"
        self.assertEqual(run(source), "2")

    def test_index_positive_and_negative(self):
        source = 'let xs = ["a", "b", "c"]\nprint(xs[0], xs[2], xs[-1], xs[-3])'
        self.assertEqual(run(source), "a c c a")

    def test_index_out_of_range_is_an_error(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("let xs = [1]\nprint(xs[5])")
        self.assertIn("fora dos limites", ctx.exception.message)
        self.assertEqual(ctx.exception.line, 2)

    def test_index_must_be_integer(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run('let xs = [1]\nprint(xs["a"])')
        self.assertIn("número inteiro", ctx.exception.message)

    def test_index_on_number_is_an_error(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("print((1 + 1)[0])")
        self.assertIn("só listas e mapas", ctx.exception.message)

    def test_index_assignment(self):
        source = "let xs = [1, 2, 3]\nxs[0] = 99\nprint(xs)"
        self.assertEqual(run(source), "[99, 2, 3]")

    def test_index_assignment_out_of_range_fails(self):
        source = "let xs = [1]\nxs[3] = 9"
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run(source)
        self.assertIn("fora dos limites", ctx.exception.message)

    def test_push_appends_and_returns_null(self):
        source = 'let xs = []\nlet r = push(xs, 1)\npush(xs, "dois")\nprint(xs, len(xs), r)'
        self.assertEqual(run(source), '[1, "dois"] 2 null')

    def test_push_rejects_non_lists(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run('push("texto", 1)')
        self.assertIn("espera uma lista", ctx.exception.message)

    def test_push_needs_two_arguments(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("let xs = []\npush(xs)")
        self.assertIn("espera 2 argumento(s)", ctx.exception.message)

    def test_list_concatenation_with_plus(self):
        self.assertEqual(run("print([1] + [2, 3])"), "[1, 2, 3]")

    def test_aliasing_lists_share_mutation(self):
        source = "let a = [1]\nlet b = a\na[0] = 2\nprint(b)"
        self.assertEqual(run(source), "[2]")

    def test_lists_have_own_truthiness(self):
        source = 'if [] {\n    print("sim")\n} else {\n    print("nao")\n}\nif [0] {\n    print("lista com elemento e verdadeira")\n}'
        self.assertEqual(run(source), "nao\nlista com elemento e verdadeira")

    def test_list_equality_is_deep(self):
        source = "print([1, 2] == [1, 2], [1, 2] == [2, 1], [1] == 1, [] == [])"
        self.assertEqual(run(source), "True False False True")


class MapTests(unittest.TestCase):
    def test_map_literal_and_member_access(self):
        source = 'let m = { nome: "Ana", idade: 30 }\nprint(m.nome, m.idade)'
        self.assertEqual(run(source), "Ana 30")

    def test_map_string_keys_and_index_access(self):
        source = 'let m = { "primeiro nome": "Ana" }\nprint(m["primeiro nome"])'
        self.assertEqual(run(source), "Ana")

    def test_multiline_map_literal(self):
        source = 'let m = {\n    a: 1,\n    b: 2,\n}\nprint(len(m), m.a + m.b)'
        self.assertEqual(run(source), "2 3")

    def test_empty_map(self):
        self.assertEqual(run("let m = {}\nprint(m, len(m))"), "{} 0")

    def test_missing_property_returns_null(self):
        source = 'let m = { a: 1 }\nprint(m.falta, m["falta"])'
        self.assertEqual(run(source), "null null")

    def test_member_assignment_creates_and_updates(self):
        source = 'let m = {}\nm.nome = "Ana"\nm["idade"] = 30\nprint(m, m.nome, m.idade)'
        self.assertEqual(run(source), '{nome: "Ana", idade: 30} Ana 30')

    def test_member_access_on_non_map_is_an_error(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("let x = 1\nprint(x.valor)")
        self.assertIn("só mapas têm propriedades", ctx.exception.message)

    def test_index_assignment_on_string_is_an_error(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run('let t = "abc"\nt[0] = "z"')
        self.assertIn("só listas e mapas aceitam", ctx.exception.message)

    def test_map_key_must_be_text(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("let m = { a: 1 }\nprint(m[1])")
        self.assertIn("chave de mapa", ctx.exception.message)

    def test_map_equality_is_deep(self):
        source = 'print({ a: 1 } == { a: 1 }, { a: 1 } == { a: 2 }, { a: 1 } == { b: 1 })'
        self.assertEqual(run(source), "True False False")

    def test_nested_collections_print(self):
        source = 'let m = { lista: [1, "dois"], filho: { x: true } }\nprint(m)'
        self.assertEqual(run(source), '{lista: [1, "dois"], filho: {x: True}}')

    def test_len_accepts_maps(self):
        self.assertEqual(run('let m = { a: 1, b: 2 }\nprint(len(m))'), "2")


class ForLoopTests(unittest.TestCase):
    def test_for_over_list(self):
        source = 'for nome in ["a", "b"] {\n    print(nome)\n}'
        self.assertEqual(run(source), "a\nb")

    def test_for_over_string_yields_characters(self):
        source = 'for c in "obi" {\n    print(c)\n}'
        self.assertEqual(run(source), "o\nb\ni")

    def test_for_over_map_yields_keys(self):
        source = 'let m = { x: 1, y: 2 }\nfor k in m {\n    print(k, m[k])\n}'
        self.assertEqual(run(source), "x 1\ny 2")

    def test_for_over_empty_collection_runs_zero_times(self):
        self.assertEqual(run('for x in [] {\n    print("nunca")\n}'), "")

    def test_loop_variable_is_local_to_the_loop(self):
        source = 'for x in [1] {\n    print(x)\n}\nprint(x)'
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run_source(source, filename="p.obl", output=lambda _l: None)
        self.assertIn("'x' não foi definida", ctx.exception.message)

    def test_loop_body_scope_does_not_leak(self):
        source = 'for x in [1] {\n    let interno = 1\n}\nprint(interno)'
        with self.assertRaises(OblivionRuntimeError):
            run_source(source, filename="p.obl", output=lambda _l: None)

    def test_for_rejects_non_collections(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("for x in 42 {\n    print(x)\n}")
        self.assertIn("só percorre listas, mapas", ctx.exception.message)

    def test_nested_for_loops(self):
        source = """\
for a in [1, 2] {
    for b in [10, 20] {
        print(a * b)
    }
}
"""
        self.assertEqual(run(source), "10\n20\n20\n40")

    def test_collecting_with_push_inside_for(self):
        source = """\
let dobro = []
for n in [1, 2, 3] {
    push(dobro, n * 2)
}
print(dobro)
"""
        self.assertEqual(run(source), "[2, 4, 6]")

    def test_for_inside_function(self):
        source = """\
fun somaLista(xs) {
    let total = 0
    for x in xs {
        total = total + x
    }
    return total
}
print(somaLista([1, 2, 3]))
"""
        self.assertEqual(run(source), "6")


class BreakContinueTests(unittest.TestCase):
    def test_break_exits_for_loop(self):
        source = """\
for n in [1, 2, 3, 4] {
    if n == 3 {
        break
    }
    print(n)
}
"""
        self.assertEqual(run(source), "1\n2")

    def test_continue_skips_iteration_in_for(self):
        source = """\
for n in [1, 2, 3, 4] {
    if n % 2 == 0 {
        continue
    }
    print(n)
}
"""
        self.assertEqual(run(source), "1\n3")

    def test_break_in_while_loop(self):
        source = """\
let i = 0
while true {
    i = i + 1
    if i == 3 {
        break
    }
}
print(i)
"""
        self.assertEqual(run(source), "3")

    def test_continue_in_while_loop(self):
        source = """\
let i = 0
let contagem = 0
while i < 5 {
    i = i + 1
    if i == 3 {
        continue
    }
    contagem = contagem + 1
}
print(contagem)
"""
        self.assertEqual(run(source), "4")

    def test_break_in_inner_loop_only(self):
        source = """\
for a in [1, 2] {
    for b in [10, 20, 30] {
        if b == 20 {
            break
        }
        print(a, b)
    }
}
"""
        self.assertEqual(run(source), "1 10\n2 10")

    def test_break_outside_loop_is_a_syntax_error(self):
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source("break", filename="p.obl")
        self.assertIn("dentro de um laço", ctx.exception.message)
        self.assertEqual(ctx.exception.line, 1)

    def test_continue_outside_loop_is_a_syntax_error(self):
        with self.assertRaises(OblivionSyntaxError):
            parse_source("let i = 0\ncontinue", filename="p.obl")

    def test_break_inside_function_inside_loop_is_a_syntax_error(self):
        source = "while true {\n    fun f() {\n        break\n    }\n}"
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source(source, filename="p.obl")
        self.assertIn("dentro de um laço", ctx.exception.message)

    def test_step_limit_still_protects_while_loops(self):
        with self.assertRaises(OblivionRuntimeError) as ctx:
            run("while true {\n    let a = 1\n}", max_steps=300)
        self.assertIn("limite de 300 passos", ctx.exception.message)


class SyntaxShapeTests(unittest.TestCase):
    def test_list_and_map_nodes(self):
        [statement] = parse_source("let v = [1, { a: 2 }]")
        self.assertIsInstance(statement.initializer, ListLiteral)
        inner = statement.initializer.elements[1]
        self.assertIsInstance(inner, MapLiteral)

    def test_index_and_member_nodes(self):
        [statement] = parse_source('print(perfil.nomes[0])')
        call = statement.expression
        self.assertIsInstance(call.arguments[0], Index)
        self.assertIsInstance(call.arguments[0].target, Member)

    def test_for_node(self):
        [statement] = parse_source('for x in [1] {\n    print(x)\n}')
        self.assertIsInstance(statement, ForStatement)
        self.assertEqual(statement.name, "x")

    def test_assignment_shapes(self):
        statements = parse_source('x = 1\nx[0] = 2\nx.prop = 3')
        self.assertNotIsInstance(statements[0], (IndexAssign, MemberAssign))
        self.assertIsInstance(statements[1], IndexAssign)
        self.assertIsInstance(statements[1].target, Index)
        self.assertIsInstance(statements[2], MemberAssign)
        self.assertIsInstance(statements[2].target, Member)

    def test_break_and_continue_nodes(self):
        statements = parse_source("while true {\n    break\n    continue\n}")
        body = statements[0].body.statements
        self.assertIsInstance(body[0], BreakStatement)
        self.assertIsInstance(body[1], ContinueStatement)

    def test_invalid_assignment_target(self):
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source("f(x) = 1", filename="p.obl")
        self.assertIn("lado esquerdo inválido", ctx.exception.message)

    def test_invalid_assignment_target_number(self):
        with self.assertRaises(OblivionSyntaxError):
            parse_source("1 = 2", filename="p.obl")

    def test_missing_colon_in_map(self):
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source("let m = { a 1 }", filename="p.obl")
        self.assertIn("':'", ctx.exception.message)

    def test_missing_bracket_in_index(self):
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source("let x = ys[0", filename="p.obl")
        self.assertIn("']'", ctx.exception.message)

    def test_missing_dot_name(self):
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source("print(a.)", filename="p.obl")
        self.assertIn("propriedade", ctx.exception.message)

    def test_duplicate_map_key(self):
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source("let m = { a: 1, a: 2 }", filename="p.obl")
        self.assertIn("chave repetida", ctx.exception.message)

    def test_for_requires_in(self):
        with self.assertRaises(OblivionSyntaxError) as ctx:
            parse_source("for x [1] {\n}", filename="p.obl")
        self.assertIn("'in'", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()

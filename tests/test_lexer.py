"""Testes do analisador léxico (etapa 1 do interpretador)."""
from __future__ import annotations

import unittest

from oblivion.errors import OblivionLexError
from oblivion.lexer import Lexer
from oblivion.tokens import TokenType


def lex(source: str, filename: str = "teste.obl"):
    return Lexer(source, filename).tokenize()


class LexerBasicsTests(unittest.TestCase):
    def test_simple_declaration_tokens(self):
        tokens = lex("let x = 42")
        self.assertEqual(
            [t.type for t in tokens],
            [
                TokenType.LET,
                TokenType.IDENTIFIER,
                TokenType.EQUAL,
                TokenType.NUMBER,
                TokenType.EOF,
            ],
        )
        self.assertEqual(tokens[3].literal, 42)
        self.assertEqual(tokens[3].lexeme, "42")

    def test_line_and_column_positions(self):
        tokens = lex("let a = 1\nlet b = 2")
        # linha 1
        self.assertEqual((tokens[0].line, tokens[0].column), (1, 1))   # let
        self.assertEqual((tokens[1].line, tokens[1].column), (1, 5))   # a
        self.assertEqual((tokens[3].line, tokens[3].column), (1, 9))   # 1
        # quebra de linha e segunda linha
        newline = tokens[4]
        self.assertEqual(newline.type, TokenType.NEWLINE)
        self.assertEqual((tokens[5].line, tokens[5].column), (2, 1))   # let

    def test_comments_are_ignored(self):
        tokens = lex("# isto é um comentário\nlet x = 1")
        # A linha do comentário vira só um NEWLINE; o primeiro token é o 'let'.
        self.assertEqual(tokens[0].type, TokenType.NEWLINE)
        self.assertEqual(tokens[1].type, TokenType.LET)
        self.assertEqual(tokens[1].line, 2)

    def test_blank_lines_and_windows_line_endings(self):
        tokens = lex("let a = 1\r\n\r\n\r\nlet b = 2\r\n")
        lets = [t for t in tokens if t.type is TokenType.LET]
        self.assertEqual(len(lets), 2)
        self.assertEqual(lets[1].line, 4)

    def test_keywords_versus_identifiers(self):
        tokens = lex("let letValue = true")
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)  # letValue não é keyword
        self.assertEqual(tokens[3].type, TokenType.TRUE)        # true é keyword

    def test_string_literals_and_escapes(self):
        tokens = lex(r'print("linha1\nlinha2\ttab")')
        strings = [t for t in tokens if t.type is TokenType.STRING]
        self.assertEqual(len(strings), 1)
        self.assertEqual(strings[0].literal, "linha1\nlinha2\ttab")

    def test_single_quotes_are_allowed(self):
        tokens = lex("let s = 'oi'")
        string = next(t for t in tokens if t.type is TokenType.STRING)
        self.assertEqual(string.literal, "oi")

    def test_numbers_integer_and_decimal(self):
        tokens = lex("1 2.5")
        numbers = [t for t in tokens if t.type is TokenType.NUMBER]
        self.assertEqual(numbers[0].literal, 1)
        self.assertIsInstance(numbers[0].literal, int)
        self.assertEqual(numbers[1].literal, 2.5)

    def test_operators_and_punctuation(self):
        tokens = lex("+ - * / // % == != < <= > >= = ( ) { } ,")
        types = [t.type for t in tokens if t.type is not TokenType.EOF]
        self.assertEqual(
            types,
            [
                TokenType.PLUS,
                TokenType.MINUS,
                TokenType.STAR,
                TokenType.SLASH,
                TokenType.SLASH_SLASH,
                TokenType.PERCENT,
                TokenType.EQUAL_EQUAL,
                TokenType.BANG_EQUAL,
                TokenType.LESS,
                TokenType.LESS_EQUAL,
                TokenType.GREATER,
                TokenType.GREATER_EQUAL,
                TokenType.EQUAL,
                TokenType.LEFT_PAREN,
                TokenType.RIGHT_PAREN,
                TokenType.LEFT_BRACE,
                TokenType.RIGHT_BRACE,
                TokenType.COMMA,
            ],
        )

    def test_newline_suppressed_inside_parentheses(self):
        tokens = lex("f(1,\n2)")
        self.assertNotIn(TokenType.NEWLINE, [t.type for t in tokens])

    def test_newline_emitted_outside_parentheses(self):
        tokens = lex("f(1)\n2")
        self.assertIn(TokenType.NEWLINE, [t.type for t in tokens])


class LexerErrorTests(unittest.TestCase):
    def test_invalid_character_reports_position_and_filename(self):
        with self.assertRaises(OblivionLexError) as ctx:
            lex("let x = @", filename="meu.obl")
        error = ctx.exception
        self.assertEqual(error.filename, "meu.obl")
        self.assertEqual(error.line, 1)
        self.assertEqual(error.column, 9)
        self.assertIn("erro léxico", str(error))
        self.assertIn("caractere inválido", error.message)

    def test_bang_without_equals_gives_hint(self):
        with self.assertRaises(OblivionLexError) as ctx:
            lex("let a ! b")
        self.assertIn("!=", ctx.exception.message)

    def test_ampersand_gives_logical_hint(self):
        with self.assertRaises(OblivionLexError) as ctx:
            lex("a & b")
        self.assertIn("and", ctx.exception.message)

    def test_unterminated_string(self):
        with self.assertRaises(OblivionLexError) as ctx:
            lex('let s = "abc')
        self.assertIn("string não terminada", ctx.exception.message)

    def test_unterminated_string_at_end_of_file(self):
        with self.assertRaises(OblivionLexError) as ctx:
            lex('let s = "abc\\')
        self.assertIn("string não terminada", ctx.exception.message)

    def test_string_with_raw_newline_is_unterminated(self):
        with self.assertRaises(OblivionLexError) as ctx:
            lex('let s = "abc\ndef"')
        self.assertIn("string não terminada", ctx.exception.message)

    def test_invalid_escape_sequence(self):
        with self.assertRaises(OblivionLexError) as ctx:
            lex(r'print("a\qb")')
        self.assertIn("escape", ctx.exception.message)

    def test_error_message_format(self):
        with self.assertRaises(OblivionLexError) as ctx:
            lex("let x = @", filename="prog.obl")
        text = str(ctx.exception)
        self.assertTrue(text.startswith("prog.obl:1:9: erro léxico: "))


if __name__ == "__main__":
    unittest.main()

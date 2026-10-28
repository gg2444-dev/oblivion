"""Testes do REPL interativo (executado com stdin/stdout conectados a tubos)."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_repl(stdin_text: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "oblivion"],
        cwd=PROJECT_ROOT,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=60,
    )


class ReplTests(unittest.TestCase):
    def test_simple_session_keeps_variables(self):
        result = run_repl("let x = 41\nprint(x + 1)\n:sair\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("42", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_multiline_block(self):
        session = 'if true {\n    print("bloco ok")\n}\n:sair\n'
        result = run_repl(session)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("bloco ok", result.stdout)

    def test_errors_do_not_close_the_repl(self):
        result = run_repl("print(indefinida)\nprint(\"ainda vivo\")\n:sair\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("erro em tempo de execução", result.stdout)
        self.assertIn("ainda vivo", result.stdout)

    def test_help_command(self):
        result = run_repl(":help\n:sair\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(":sair", result.stdout)


if __name__ == "__main__":
    unittest.main()

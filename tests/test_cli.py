"""Testes da linha de comando (``python -m oblivion``) — usam subprocessos locais."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_HELLO = """\
Hello, Alex
Your age: 16
Calculation: 20
Are you a teenager? True
"""


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Executa ``python -m oblivion <args>`` a partir da raiz do projeto."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "oblivion", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=60,
    )


class CliFileTests(unittest.TestCase):
    def test_runs_hello_example_with_exact_output(self):
        result = run_cli("examples/hello.obl")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED_HELLO)
        self.assertEqual(result.stderr, "")

    def test_runs_fibonacci_example(self):
        result = run_cli("examples/fibonacci.obl")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Fibonacci(10) = 55\n")

    def test_runs_collections_example(self):
        result = run_cli("examples/collections.obl")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Jogadores: ["Alex", "Lucas", "Ryan", "Maria"] total: 4', result.stdout)
        self.assertIn("Welcome, Alex!", result.stdout)
        self.assertIn("Welcome, Ryan!", result.stdout)
        self.assertNotIn("Welcome, Lucas!", result.stdout)
        self.assertIn('nome: Oblivion | faltando: null', result.stdout)
        self.assertIn("Quadrados: [1, 4, 16]", result.stdout)

    def test_help_flag(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout)
        self.assertIn("python -m oblivion", result.stdout)
        self.assertIn("--max-steps", result.stdout)

    def test_version_flag(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("0.2.0", result.stdout)

    def test_missing_file_is_friendly(self):
        result = run_cli("arquivo_que_nao_existe.obl")
        self.assertEqual(result.returncode, 1)
        self.assertIn("erro ao ler o arquivo", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_syntax_error_shows_file_line_column_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "quebrado.obl"
            path.write_text('print("oi"\n', encoding="utf-8")
            result = run_cli(str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("erro de sintaxe", result.stderr)
        self.assertIn(":1:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_runtime_error_shows_position_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "indif.obl"
            path.write_text("let a = 1\nprint(a + \"x\")\n", encoding="utf-8")
            result = run_cli(str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("erro em tempo de execução", result.stderr)
        self.assertIn("indif.obl:2:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_infinite_loop_is_stopped_by_max_steps(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "loop.obl"
            path.write_text("while true {\n}\n", encoding="utf-8")
            result = run_cli("--max-steps", "2000", str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("limite de 2000 passos", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_max_steps_value(self):
        result = run_cli("--max-steps", "0", "examples/hello.obl")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--max-steps", result.stderr)


if __name__ == "__main__":
    unittest.main()

"""Testes de segurança: o interpretador não deve executar código do host.

Estas verificações garantem que:

* nenhum ``eval``/``exec`` do Python é usado para rodar código Oblivion;
* os módulos centrais não importam bibliotecas perigosas do Python
  (só o ``__main__`` pode usar ``sys``, por ser a CLI).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "oblivion"

#: Módulos do Python que não podem aparecer nos módulos centrais.
FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "socket", "pathlib", "importlib", "ctypes", "shutil"}

CORE_MODULES = [
    "tokens.py",
    "lexer.py",
    "ast_nodes.py",
    "parser.py",
    "interpreter.py",
    "errors.py",
    "__init__.py",
]


class SafetyTests(unittest.TestCase):
    def test_no_eval_or_exec_in_package(self):
        pattern = re.compile(r"(?<![\w.])(eval|exec)\s*\(")
        for name in CORE_MODULES + ["__main__.py"]:
            with self.subTest(module=name):
                source = (PACKAGE_DIR / name).read_text(encoding="utf-8")
                match = pattern.search(source)
                if match is not None:
                    self.fail(f"{name} contém chamada a {match.group(1)}() do Python")

    def test_core_modules_do_not_import_dangerous_libraries(self):
        import_pattern = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", re.MULTILINE)
        for name in CORE_MODULES:
            source = (PACKAGE_DIR / name).read_text(encoding="utf-8")
            for module in import_pattern.findall(source):
                with self.subTest(module=name, imported=module):
                    self.assertNotIn(
                        module.split(".")[0],
                        FORBIDDEN_IMPORTS,
                        f"{name} importa {module}",
                    )

    def test_core_modules_do_not_open_files(self):
        for name in CORE_MODULES:
            source = (PACKAGE_DIR / name).read_text(encoding="utf-8")
            with self.subTest(module=name):
                self.assertNotIn("open(", source)


if __name__ == "__main__":
    unittest.main()

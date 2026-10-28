"""Linha de comando do Oblivion: ``python -m oblivion``.

Modos de uso:

* ``python -m oblivion arquivo.obl`` — executa um arquivo;
* ``python -m oblivion`` — inicia o REPL interativo;
* ``python -m oblivion --help`` / ``--version`` — ajuda e versão.

Erros da linguagem são impressos no formato ``arquivo:linha:coluna: tipo:
mensagem`` (sem traceback do Python) e o processo sai com código 1.
"""
from __future__ import annotations

import argparse
import sys

from . import __version__, run_source
from .errors import OblivionError
from .interpreter import DEFAULT_MAX_STEPS, Interpreter

PROG = "python -m oblivion"

_EPILOG = """\
exemplos:
  python -m oblivion examples/hello.obl   executa um programa
  python -m oblivion                      inicia o REPL interativo
  python -m oblivion --max-steps 20000 x.obl   aumenta o limite de passos

No REPL digite :help para ajuda e :sair para sair.
"""


def build_arg_parser() -> argparse.ArgumentParser:
    """Monta o analisador de argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Oblivion — interpretador da linguagem de programação Oblivion.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        nargs="?",
        metavar="arquivo.obl",
        help="arquivo .obl a ser executado (omitir inicia o REPL)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"Oblivion {__version__}",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=DEFAULT_MAX_STEPS,
        metavar="N",
        help=f"limite de passos de execução (padrão: {DEFAULT_MAX_STEPS})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI. Devolve o código de saída do processo."""
    args = build_arg_parser().parse_args(argv)

    if args.max_steps <= 0:
        print("erro: --max-steps deve ser um número positivo", file=sys.stderr)
        return 2

    if args.file is None:
        return run_repl(max_steps=args.max_steps)

    try:
        with open(args.file, encoding="utf-8") as handle:
            source = handle.read()
    except OSError as exc:
        detail = exc.strerror or str(exc)
        print(f"{args.file}: erro ao ler o arquivo: {detail}", file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        print(f"{args.file}: erro ao ler o arquivo: o texto não está em UTF-8", file=sys.stderr)
        return 1

    try:
        run_source(source, filename=args.file, max_steps=args.max_steps)
    except OblivionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nprograma interrompido pelo usuário", file=sys.stderr)
        return 130
    return 0


# ----------------------------------------------------------------------
# REPL interativo
# ----------------------------------------------------------------------
def _brace_balance(text: str) -> int:
    """Conta chaves não fechadas, ignorando comentários e textos entre aspas."""
    balance = 0
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(text):
        ch = text[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            while index < len(text) and text[index] != "\n":
                index += 1
            continue
        elif ch == "{":
            balance += 1
        elif ch == "}":
            balance -= 1
        index += 1
    return balance


def run_repl(max_steps: int = DEFAULT_MAX_STEPS) -> int:
    """Executa o laço do REPL (as variáveis persistem entre comandos)."""
    print(f"Oblivion {__version__} — REPL interativo. Digite :help para ajuda.")
    interpreter = Interpreter(max_steps=max_steps, filename="<repl>")
    buffer = ""

    while True:
        try:
            line = input("... " if buffer else "obl> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\n(use :sair para encerrar)")
            continue

        stripped = line.strip()
        if not buffer:
            if stripped in (":sair", ":exit", ":quit", ":q"):
                break
            if stripped == ":help":
                print("Comandos: :sair (encerra), :help (esta ajuda).")
                print("Digite código Oblivion; blocos { } podem ocupar várias linhas.")
                continue
            if not stripped:
                continue

        buffer += line + "\n"
        if _brace_balance(buffer) > 0:
            continue  # bloco ainda aberto: pede mais linhas

        source, buffer = buffer, ""
        interpreter.steps = 0  # cada comando tem seu próprio limite de passos
        try:
            run_source(source, filename="<repl>", interpreter=interpreter)
        except OblivionError as exc:
            print(str(exc))
        except RecursionError:
            print("<repl>: erro em tempo de execução: profundidade de recursão excedida")
        except KeyboardInterrupt:
            print("\ncomando interrompido")
    return 0


if __name__ == "__main__":
    sys.exit(main())

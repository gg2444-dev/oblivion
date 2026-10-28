# Oblivion

**Oblivion** é uma linguagem de programação moderna, simples e de propósito geral,
inspirada na usabilidade do Python e do JavaScript. Este repositório contém o
**interpretador v0.2** da linguagem, escrito em Python 3.11+ **sem dependências
externas** (zero deps).

> ⚠️ **Aviso importante:** Oblivion é um projeto **educacional**. O interpretador
> **não** é um ambiente de segurança endurecido (*sandbox*). Não rode código de
> pessoas desconhecidas esperando proteção total. Ele não executa código do host,
> não importa módulos a partir do código Oblivion e não acessa arquivos pela
> linguagem, mas foi feito para ensinar, não para isolar código hostil.

---

## Sumário

1. [Pré-requisitos](#1-pré-requisitos)
2. [Estrutura do projeto](#2-estrutura-do-projeto)
3. [Como rodar (sem instalação)](#3-como-rodar-sem-instalação)
4. [Primeiro programa](#4-primeiro-programa)
5. [Sintaxe suportada](#5-sintaxe-suportada)
6. [Precedência de operadores](#6-precedência-de-operadores)
7. [Variáveis](#7-variáveis)
8. [Condicionais](#8-condicionais)
9. [Laços](#9-laços)
10. [Funções](#10-funções)
11. [Funções embutidas](#11-funções-embutidas)
12. [Erros](#12-erros)
13. [Gramática (EBNF)](#13-gramática-ebnf)
14. [Como rodar os testes](#14-como-rodar-os-testes)
15. [Limitações atuais](#15-limitações-atuais)
16. [Segurança](#16-segurança)
17. [Roadmap (ainda NÃO implementado)](#17-roadmap-ainda-não-implementado)
18. [Licença](#18-licença)

---

## 1. Pré-requisitos

- **Python 3.11 ou superior** (`python --version`).
- Nenhum pacote adicional é necessário: o interpretador não tem dependências.
- Windows, macOS ou Linux.

## 2. Estrutura do projeto

```
oblivion/
├── pyproject.toml        # metadados do projeto (opcional para rodar)
├── LICENSE               # licença MIT
├── README.md             # este arquivo
├── oblivion/             # pacote do interpretador (layout plano)
│   ├── __init__.py       # API pública: run_source(), parse_source()...
│   ├── __main__.py       # CLI: python -m oblivion (arquivo, REPL, --help)
│   ├── tokens.py         # tipos de token e palavras-chave
│   ├── lexer.py          # analisador léxico (caracteres → tokens)
│   ├── ast_nodes.py      # nós da árvore sintática abstrata (AST)
│   ├── parser.py         # parser recursivo (tokens → AST) + gramática EBNF
│   ├── interpreter.py    # runtime: escopos, avaliação, limites, builtins
│   └── errors.py         # erros léxicos, sintáticos e de execução
├── examples/
│   ├── hello.obl         # programa de exemplo obrigatório
│   ├── fibonacci.obl     # funções e recursão
│   ├── loops.obl         # while, if/else e atribuição
│   └── collections.obl   # listas, mapas, for, break/continue
└── tests/                # testes automatizados (unittest, sem rede)
    ├── test_lexer.py
    ├── test_parser.py
    ├── test_language.py
    ├── test_functions.py
    ├── test_collections.py  # listas, mapas, for, break/continue
    ├── test_cli.py       # executa `python -m oblivion` de verdade
    ├── test_repl.py      # sessão de REPL via entrada/saída padrão
    └── test_safety.py    # garante que não há eval/exec no interpretador
```

> **Por que layout plano (sem `src/`)?** Para que
> `python -m oblivion arquivo.obl` e `python -m unittest` funcionem **direto da
> raiz do projeto, sem nenhum passo de instalação**. Um `pip install -e .` é
> opcional (se quiser o comando `oblivion` global).

## 3. Como rodar (sem instalação)

Você pode executar a Oblivion diretamente do código-fonte, sem instalar dependências externas.

Abra um terminal na raiz do projeto, na pasta que contém o arquivo `pyproject.toml`.

### Windows — PowerShell

**Executar um programa**

```powershell
python -m oblivion examples/hello.obl
```

**Ajuda e versão**

```powershell
python -m oblivion --help
python -m oblivion --version
```

**Executar os testes**

```powershell
python -m unittest
```

### macOS / Linux

**Executar um programa**

```bash
python3 -m oblivion examples/hello.obl
```

**Ajuda e versão**

```bash
python3 -m oblivion --help
python3 -m oblivion --version
```

**Executar os testes**

```bash
python3 -m unittest
```

### REPL interativo

Para iniciar o modo interativo, execute:

```bash
python -m oblivion
```

Exemplo:

```text
Oblivion 0.2.0 — REPL interativo. Digite :help para ajuda.
obl> let x = 41
obl> print(x + 1)
42
obl> :sair
```

No REPL, `:help` mostra a ajuda e `:sair`, `:exit` ou `:q` encerra a sessão.

### Instalação opcional

Para instalar a Oblivion em modo editável e disponibilizar o comando global, execute na raiz do projeto:

```bash
python -m pip install -e .
```

Depois, você poderá executar:

```bash
oblivion examples/hello.obl
oblivion --version
```

O comando global depende de a pasta de executáveis do Python estar disponível no `PATH`.

## 4. Primeiro programa

Crie `ola.obl` (extensão **`.obl`**):

```oblivion
# My first Oblivion program
let name = "Alex"
let age = 16
let result = 10 + 5 * 2
print("Hello, " + name)
print("Your age:", age)
print("Calculation:", result)
print("Are you a teenager?", age >= 13 and age <= 19)
```

Execute:

```bash
python -m oblivion ola.obl
```

Saída:

```
Hello, Alex
Your age: 16
Calculation: 20
Are you a teenager? True
```

Regras do arquivo: **uma instrução por linha**, linhas em branco são ignoradas e
comentários começam com `#` e vão até o fim da linha. Blocos de código usam
chaves `{ ... }` (em `if`, `while` e `fun`).

## 5. Sintaxe suportada

Tudo abaixo está implementado e testado na v0.2:

| Recurso | Exemplo |
| --- | --- |
| Números inteiros e decimais | `42`, `3.14` |
| Textos (aspas simples ou duplas) | `"oi"`, `'oi'` com escapes `\n \t \r \\ \" \'` |
| Booleanos e nulo | `true`, `false`, `null` |
| **Listas** | `["a", 1, null]`, índice `xs[0]`, `xs[-1]`, atribuição `xs[0] = v` |
| **Mapas** | `{ nome: "Ana", idade: 3 }`, propriedade `m.nome`, chave `m["nome"]` |
| Variáveis | `let x = 1` (declaração) e `x = 2` (reatribuição) |
| Aritmética | `+ - * / // %` (e `lista + lista` concatena) |
| Comparações | `== != < <= > >=` (`==` é profundo para listas e mapas) |
| Lógicos | `and`, `or`, `not` (com curto-circuito) |
| Parênteses | `(1 + 2) * 3` |
| Condicional | `if cond { ... } else { ... }` e `else if` |
| Laço condicional | `while cond { ... }` |
| **Laço de coleção** | `for nome in colecao { ... }` (lista, mapa ou texto) |
| **Saída/pulo de laço** | `break` e `continue` (só dentro de `while`/`for`) |
| Funções | `fun nome(a, b) { return a + b }` e chamadas `nome(x, y)` |
| Impressão | `print()` com zero ou mais argumentos (separados por espaço) |
| Comentários | `# até o fim da linha` |
| Expressões como instrução | `1 + 1` (valor avaliado e descartado) |

Detalhes de semântica:

- **Variáveis são mutáveis.** `let` declara uma vez no escopo atual; `=` muda o
  valor depois. Redeclarar `let x` **no mesmo escopo** é erro. Atribuir a uma
  variável nunca declarada também é erro (não cria “por acidente”).
- **Regra de verdade:** `false`, `null`, `0` e `""` são falsos; todo o resto é
  verdadeiro.
- **`print`** escreve cada argumento separado por um espaço e usa `True`/`False`
  (maiúscula) ao imprimir booleanos — note que os literais no código são
  `true`/`false` (minúscula).
- **`/` sempre gera decimal** (`10 / 5` → `2.0`); use `//` para divisão inteira
  (arredondando para baixo: `-7 // 2` → `-4`) e `%` para resto.
- **`==` é estrito quanto a tipos:** `true == 1` → `false`.
- **`+` só soma número+número ou texto+texto**; misturar tipos é erro (sem
  conversão automática).
- **Funções:** parâmetros e `let` são locais; sem `return` a função devolve
  `null`; closures funcionam (funções aninhadas enxergam variáveis do escopo onde
  foram declaradas); recursão é permitida (dentro dos limites de execução).
- **`return` fora de função é erro de sintaxe.**
- **Listas e mapas são mutáveis e compartilhados por referência:** ao fazer
  `let b = a`, ambas apontam para a mesma lista — mudar `a[0]` muda `b` também.
- **Índices de lista:** começam em `0`; negativos contam do fim (`xs[-1]` é o
  último). Índice fora dos limites é **erro de execução** (mensagem com linha e
  coluna). Para crescer a lista use `push(lista, valor)`.
- **Chaves de mapa:** sempre textos. `m.chave` e `m["chave"]` são equivalentes;
  propriedade/chave **inexistente devolve `null`** (não é erro). Atribuir cria
  a chave se ela não existir (`m.novo = 1`).
- **`print` de coleções:** textos dentro de listas/mapas aparecem entre aspas —
  ex.: `{nome: "Ana", notas: [1, 2]}`.
- **`==` em coleções compara por conteúdo** (profundo), não por identidade.
- **Coleções vazias são falsas:** `if [] { ... }` não entra no ramo.
- **`for`** percorre: lista → elementos, mapa → chaves, texto → caracteres; a
  variável do laço existe **só dentro do bloco** (é declarada a cada execução do
  `for`).

Exemplo juntando listas, mapas e `for`:

```oblivion
let notas = []
push(notas, 8)
push(notas, 6)

let aluno = { nome: "Ana", aprovado: true }
aluno["media"] = (notas[0] + notas[1]) / 2

for chave in aluno {
    print(chave, "=", aluno[chave])
}
# nome = Ana
# aprovado = True
# media = 7.0
```

## 6. Precedência de operadores

Da **menor para a maior** precedência (linhas de baixo para cima):

| # | Operadores | Associatividade |
| --- | --- | --- |
| 1 | `or` | esquerda → direita |
| 2 | `and` | esquerda → direita |
| 3 | `not` (unário) | direita → esquerda |
| 4 | `==` `!=` `<` `<=` `>` `>=` | esquerda → direita |
| 5 | `+` `-` | esquerda → direita |
| 6 | `*` `/` `//` `%` | esquerda → direita |
| 7 | `-` (unário) | direita → esquerda |
| 8 | chamada `f(x)`, parênteses, literais | — |

Exemplos:

- `10 + 5 * 2` → `20` (multiplicação primeiro)
- `(10 + 5) * 2` → `30` (parênteses mudam tudo)
- `not a == b` significa `not (a == b)`
- `age >= 13 and age <= 19` → comparações antes do `and`

## 7. Variáveis

```oblivion
let nome = "Alex"     # declara
nome = "Maria"        # reatribui (mutável)
print(nome, len(nome)) # Maria 5
```

- Escopo: `let` dentro de `{ ... }` (bloco, `if`, `while` ou função) vale só
  naquele bloco e nos blocos filhos.
- Ler variável inexistente → erro com arquivo, linha e coluna.
- `print` e `len` são nomes embutidos e **não podem** ser redeclarados.

## 8. Condicionais

```oblivion
let nota = 8

if nota >= 7 {
    print("aprovado")
} else if nota >= 5 {
    print("recuperacao")
} else {
    print("reprovado")
}
```

A condição é avaliada com a regra de verdade (ver §5). `else` e `else if` são
opcionais. `if` e `while` **exigem** o bloco com chaves.

## 9. Laços

`while` repete enquanto a condição for verdadeira:

```oblivion
let i = 1
let soma = 0
while i <= 10 {
    soma = soma + i
    i = i + 1
}
print(soma)   # 55
```

`for` percorre uma lista, as chaves de um mapa ou os caracteres de um texto:

```oblivion
let jogadores = ["Alex", "Lucas", "Ryan"]
for nome in jogadores {
    if nome == "Lucas" {
        continue          # pula para o próximo
    }
    if nome == "Ryan" {
        break             # sai do laço
    }
    print("Welcome, " + nome + "!")
}
```

- `break` sai do laço mais interno; `continue` pula para a próxima iteração.
  Ambos **só podem aparecer dentro de `while`/`for`** (fora é erro de sintaxe;
  também não funcionam dentro de funções declaradas no laço).
- Não existe `for` clássico com contador — use `while` para contagem e `for`
  para coleções.
- **Limite de execução:** para evitar laços infinitos, o interpretador conta
  passos de execução e para com um erro claro. Padrão: **1.000.000** passos.
  Ajuste pela CLI: `python -m oblivion --max-steps 5000000 prog.obl`.

## 10. Funções

```oblivion
fun soma(a, b) {
    return a + b
}

fun fat(n) {
    if n <= 1 {
        return 1
    }
    return n * fat(n - 1)
}

print(soma(2, 3))   # 5
print(fat(5))       # 120
```

- Parâmetros e variáveis `let` são **locais** de cada chamada.
- Sem `return`, a função devolve `null`; `return` sem valor também devolve `null`.
- Passar número errado de argumentos → erro de execução.
- Funções são valores: podem ser passadas como argumento e retornadas
  (necessário para *closures*).

## 11. Funções embutidas

| Função | Uso | Observação |
| --- | --- | --- |
| `print(...)` | `print("oi", 42)` | zero ou mais argumentos; separa com espaço; devolve `null` |
| `len(x)` | `len("abc")` → `3` | exatamente 1 argumento; aceita texto, lista e mapa |
| `push(lista, v)` | `push(xs, 1)` | exatamente 2 argumentos; anexa no fim da lista; devolve `null` |

## 12. Erros

Três categorias, sempre com **arquivo, linha e coluna**, e **sem traceback do
Python**:

| Categoria | Quando acontece | Exemplo de mensagem |
| --- | --- | --- |
| Erro léxico | caractere inválido, texto sem fechar | `prog.obl:1:9: erro léxico: caractere inválido '@'` |
| Erro de sintaxe | código com forma errada | `prog.obl:2:9: erro de sintaxe: esperava uma expressão (encontrado '=')` |
| Erro em tempo de execução | valor/variável/tipo errado | `prog.obl:1:7: erro em tempo de execução: variável 'y' não foi definida (use 'let y = ...')` |

Mais exemplos:

```bash
$ python -m oblivion prog.obl
prog.obl:2:1: erro de sintaxe: esperava ')' após a expressão (encontrado 'print')
# código de saída 1

$ python -m oblivion inexistente.obl
inexistente.obl: erro ao ler o arquivo: No such file or directory
# código de saída 1
```

Saída do processo: `0` = sucesso, `1` = erro da linguagem/arquivo, `2` = uso
incorreto da CLI.

## 13. Gramática (EBNF)

Esta é a gramática **real**, idêntica à documentada em `oblivion/parser.py`:

```ebnf
program        = { NEWLINE | statement } EOF ;

statement      = letStmt
               | ifStmt
               | whileStmt
               | forStmt
               | breakStmt
               | continueStmt
               | funDecl
               | returnStmt
               | assignStmt
               | exprStmt ;

letStmt        = "let" IDENT "=" expression lineEnd ;
assignStmt     = assignTarget "=" expression lineEnd ;
assignTarget   = IDENT | indexExpr | memberExpr ;   (* lado esquerdo válido *)
ifStmt         = "if" expression block [ "else" ( ifStmt | block ) ] ;
whileStmt      = "while" expression block ;
forStmt        = "for" IDENT "in" expression block ;
breakStmt      = "break" lineEnd ;         (* só dentro de while/for *)
continueStmt   = "continue" lineEnd ;      (* só dentro de while/for *)
funDecl        = "fun" IDENT "(" [ params ] ")" block ;
params         = IDENT { "," IDENT } ;        (* sem repetidos, máx. 255 *)
returnStmt     = "return" [ expression ] lineEnd ;   (* só dentro de fun *)
exprStmt       = expression lineEnd ;
block          = "{" { NEWLINE | statement } "}" ;
lineEnd        = NEWLINE | "}" | EOF ;        (* uma instrução por linha *)

expression     = orExpr ;
orExpr         = andExpr { "or" andExpr } ;
andExpr        = notExpr { "and" notExpr } ;
notExpr        = "not" notExpr | comparison ;
comparison     = term { ( "==" | "!=" | "<" | "<=" | ">" | ">=" ) term } ;
term           = factor { ( "+" | "-" ) factor } ;
factor         = unary { ( "*" | "/" | "//" | "%" ) unary } ;
unary          = "-" unary | postfix ;
postfix        = primary { call | indexExpr | memberExpr } ;
call           = "(" [ args ] ")" ;
indexExpr      = "[" expression "]" ;
memberExpr     = "." IDENT ;
args           = expression { "," expression } ;     (* máx. 255 *)
primary        = NUMBER
               | STRING
               | "true" | "false" | "null"
               | listLit
               | mapLit
               | IDENT
               | "(" expression ")" ;
listLit        = "[" [ elements ] "]" ;   (* multilinha: NEWLINEs ignorados *)
elements       = expression { "," expression } [ "," ] ;
mapLit         = "{" [ mapEntries ] "}" ;
mapEntries     = mapEntry { "," mapEntry } [ "," ] ;
mapEntry       = ( IDENT | STRING ) ":" expression ;
```

Notas: `IDENT` é um nome (`[A-Za-z_][A-Za-z0-9_]*`); `NEWLINE` é suprimido
dentro de parênteses (expressões podem quebrar em várias linhas) e ignorado
dentro de listas/mapas literais; comentários `# ...` não geram tokens; literais
de lista/mapa só aparecem em posição de expressão (um `{` que começa uma
instrução continua sendo erro — blocos seguem `if`, `while`, `for` e `fun`).

## 14. Como rodar os testes

Na raiz do projeto (sem dependências, sem rede):

```powershell
# Windows PowerShell
python -m unittest
```

```bash
# macOS/Linux
python3 -m unittest
```

Para ver detalhes de cada teste:

```bash
python -m unittest discover -s tests -t . -v
```

A suíte cobre, entre outros: o exemplo obrigatório com saída exata, precedência
e parênteses, textos e variáveis, booleanos/comparações, tokens inválidos e
sintaxe quebrada, variáveis indefinidas, ramos `if/else`, `while` com limite de
passos, funções/recursão/closures, **listas, mapas, indexação, `for`,
`break`/`continue`**, a CLI (`--help`, `--version`, execução de arquivo, erros
sem traceback) e verificações de segurança (sem `eval`/`exec`).

## 15. Limitações atuais

- Sem módulos/`import` nem biblioteca padrão (além de `print`, `len` e `push`).
- Sem interpolação de texto (`"${x}"`): use concatenação com `+`.
- Sem `for` com contador numérico (use `while`) e sem `for` com índice/valor
  simultâneos (`enumerate`).
- Sem notação de exponência (`1e9`) nem números complexos.
- Sem anotações de tipo nem análise estática: os tipos são checados em tempo de
  execução.
- Sem otimizações de desempenho: é um interpretador de AST, feito para clareza.
- Números decimais usam `float` do Python (limites binários conhecidos).
- Não há try/catch na linguagem: erros de execução sempre encerram o programa
  (com mensagem clara). Por isso `mapa.chave` inexistente devolve `null` em vez
  de falhar.
- Um limite fixo de passos protege contra laços infinitos; memória/alocação não é
  limitada além do tamanho máximo de textos (1.000.000 de caracteres) e de
  listas/mapas (1.000.000 de elementos/chaves).
- Recursão muito profunda encerra com erro amigável de “profundidade de
  recursão” (a pilha do Python é finita).

## 16. Segurança

O que o interpretador **faz** para se proteger:

- nunca usa `eval`/`exec` do Python para rodar código Oblivion (há teste automático
  garantindo isso);
- não expõe objetos nem builtins do Python à linguagem (só `print` e `len`);
- não permite importar módulos, ler/escrever arquivos ou acessar a rede a partir
  do código Oblivion;
- impõe limite de passos de execução (anti laço infinito) e limite de tamanho de
  texto.

O que ele **não** é: um *sandbox* endurecido. O interpretador roda no mesmo
processo do Python, não isola memória/CPU de forma agressiva e não foi auditado
para ataques. Use apenas em contexto educacional/confiável.

## 17. Roadmap (ainda NÃO implementado)

Itens planejados para versões futuras — **não existem hoje**:

- Interpolação de texto (`"Olá, ${nome}!"`)
- Sintaxe opcional de fim de instrução com `;` (se a comunidade quiser)
- Módulos e sistema de importação
- Biblioteca padrão (mais funções embutidas: ordenação, entrada de dados...)
- Gerenciador de pacotes
- Formatador oficial e *lint*
- Verificação estática de tipos
- Compilador/VM com bytecode
- Ferramentas de editor (LSP, realce de sintaxe)
- Melhorias de desempenho e limites de memória configuráveis

## 18. Licença

MIT (arquivo [`LICENSE`](LICENSE)). A escolha da licença MIT deve-se ao
objetivo educacional do projeto: permissão máxima de uso, estudo e modificação,
com manutenção do aviso de copyright.

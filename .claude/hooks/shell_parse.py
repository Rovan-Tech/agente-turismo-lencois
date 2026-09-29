"""Análise sintática de comandos de shell para o guarda de comandos (`guard_bash.py`).

Divide o comando em segmentos (quebras de linha, `;`, `&&`, `||`, `|`), descarta corpos de heredoc
que não são código de shell e remove wrappers (`sudo`, `env`, `timeout`, ...) para achar o
executável.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

OPERATORS = {"&&", "||", ";", "|", "&", "(", ")"}
SHELLS = {"sh", "bash", "zsh", "dash"}
WRAPPERS = {"sudo", "env", "command", "nohup", "time", "timeout", "nice", "ionice", "exec"}
WRAPPERS |= {"xargs", "stdbuf", "!"}
WRAPPER_OPTS_WITH_ARG = {"-u", "-g", "-C", "-h", "-p", "-r", "-t", "-n", "-s", "-k", "-I", "-L"}
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")
DURATION_RE = re.compile(r"^\d+(\.\d+)?[smhd]?$")

Segment = tuple[str, list[str]]


def _next_quote(quote: str, char: str) -> str:
    """Estado de aspas após ler `char` (vazio = fora de aspas)."""
    if quote:
        return "" if char == quote else quote
    return char if char in "'\"" else ""


def split_unquoted_newlines(command: str) -> list[str]:
    """Divide o comando nas quebras de linha fora de aspas (barra + quebra é continuação)."""
    lines: list[str] = []
    current: list[str] = []
    quote = ""
    index = 0
    while index < len(command):
        char = command[index]
        if char == "\\" and quote != "'" and index + 1 < len(command):
            current.append("" if command[index + 1] == "\n" else char + command[index + 1])
            index += 2
            continue
        if char == "\n" and not quote:
            lines.append("".join(current))
            current = []
        else:
            current.append(char)
        quote = _next_quote(quote, char)
        index += 1
    lines.append("".join(current))
    return lines


def heredoc_start(line: str) -> tuple[str | None, bool]:
    """Terminador do heredoc aberto na linha e se o corpo é código de shell (deve ser analisado)."""
    match = HEREDOC_RE.search(line)
    if not match:
        return None, False
    first = parse_command(line)
    return match.group(2), bool(first) and verb_of(first[0][1]) in SHELLS


def join_lines(command: str) -> str:
    """Troca quebras de linha por `;` e descarta corpos de heredoc (exceto os de shells)."""
    kept: list[str] = []
    terminator: str | None = None
    keep_body = False
    for line in split_unquoted_newlines(command):
        in_body = terminator is not None
        if in_body and line.strip() == terminator:
            terminator = None
        elif in_body:
            if keep_body:
                kept.append(line)
        else:
            kept.append(line)
            terminator, keep_body = heredoc_start(line)
    return " ; ".join(kept)


def parse_command(command: str) -> list[Segment]:
    """Divide uma linha em segmentos `(operador_anterior, tokens)`."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segments: list[Segment] = []
    separator = ""
    current: list[str] = []
    for token in tokens:
        if token in OPERATORS:
            if current:
                segments.append((separator, current))
            separator, current = token, []
        else:
            current.append(token)
    if current:
        segments.append((separator, current))
    return segments


def effective_tokens(tokens: list[str]) -> tuple[list[str], set[str]]:
    """Tokens do comando real, sem `sudo`/`env`/`timeout`/... e as atribuições `VAR=x`."""
    wrappers: set[str] = set()
    index = 0
    while index < len(tokens) and (tokens[index] in WRAPPERS or re.match(r"^\w+=", tokens[index])):
        wrappers.add(tokens[index])
        index += 1
        while index < len(tokens) and tokens[index].startswith("-"):
            index += 2 if tokens[index] in WRAPPER_OPTS_WITH_ARG else 1
        if index < len(tokens) and DURATION_RE.match(tokens[index]):
            index += 1
    return tokens[index:], wrappers


def verb_of(tokens: list[str]) -> str:
    """Executável do comando (depois de remover os wrappers)."""
    effective, _ = effective_tokens(tokens)
    return Path(effective[0]).name if effective else ""

"""Hook PreToolUse (Bash): guarda de comandos perigosos.

Bloqueia comandos destrutivos, commit/push na branch principal, instalação de pacotes fora do
gerenciador do projeto, leitura/escrita de segredos e escrita do Claude em `.claude/state` e
`.claude/reports`. Pede confirmação para qualquer `git commit`/`git push` e para regravar as
linhas de base do gate (o Patrick autoriza cada um).

O comando é dividido em segmentos (quebras de linha, `;`, `&&`, `||`, `|`) e tokenizado com
`shlex`, então o texto de uma mensagem de commit ou de um `echo` não dispara regras de outros
comandos. `bash -c`, `eval` e `$(...)` são analisados de forma recursiva. Isto é uma rede de
segurança contra acidentes, não uma fronteira de segurança: um script arbitrário pode contorná-la.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

import hook_common as common
from shell_parse import (
    SHELLS,
    Segment,
    effective_tokens,
    join_lines,
    parse_command,
    verb_of,
)

PROTECTED_BRANCHES = {"main", "master"}
READ_ONLY_VERBS = {
    "cat",
    "ls",
    "head",
    "tail",
    "less",
    "grep",
    "rg",
    "jq",
    "wc",
    "stat",
    "file",
}
DB_CLIENTS = {"psql", "sqlite3", "mysql", "mariadb", "sqlcmd", "duckdb"}
MESSAGE_OPTS = {"-m", "--message", "-b", "--body", "--title", "-F", "--body-file"}
BROAD_TARGETS = {"*", ".*", "./*", "/*", "/", ".", "..", "./"}
GIT_OPTS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
BASELINE_FLAGS = ("--write-mypy-baseline", "--update-baseline")
PIP_HINT = (
    "Instale pacotes só no venv do projeto: "
    "backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt."
)
STATE_MESSAGE = ".claude/state e .claude/reports só os hooks gravam."

SQL_RE = re.compile(r"\b(drop\s+(table|database|schema|index)|truncate\s+table\s+\w+)", re.I)
SECRET_RE = re.compile(r"(^|[\s/\"'<>=:])\.env(\*|\.(?!example\b)[\w.*-]+)?(?=$|[\s\"'|;&)])")
KEY_FILE_RE = re.compile(r"\.(pem|key|p12|pfx)\b|id_(rsa|ed25519)")
STATE_RE = re.compile(r"\.claude/(state|reports)\b")
WRITE_HINT_RE = re.compile(
    r">(?!&)(?!\s*/dev/null)|\btee\b|\bsed\s+-\S*i|\b(rm|mv|cp|touch|mkdir|truncate|dd)\b"
)
SUBST_RE = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
MAX_DEPTH = 3

Decision = tuple[str, str]


def git_call(tokens: list[str]) -> tuple[str, list[str]] | None:
    """Subcomando do git e seus argumentos, pulando as opções globais (`-C x`, `-c k=v`)."""
    effective, _ = effective_tokens(tokens)
    if not effective or Path(effective[0]).name != "git":
        return None
    index = 1
    while index < len(effective) and effective[index].startswith("-"):
        index += 2 if effective[index] in GIT_OPTS_WITH_ARG else 1
    if index >= len(effective):
        return None
    return effective[index], effective[index + 1 :]


def has_flag(args: list[str], short: str, long: tuple[str, ...] = ()) -> bool:
    """Os argumentos têm a flag curta (agrupada ou não) ou alguma das longas?"""
    for arg in args:
        if arg in long or any(arg.startswith(f"{name}=") for name in long):
            return True
        if arg.startswith("-") and not arg.startswith("--") and short in arg[1:]:
            return True
    return False


def destructive_git(sub: str, args: list[str]) -> Decision | None:
    """`push --force`, `reset --hard` e `clean -f`."""
    force_push = has_flag(args, "f", ("--force", "--force-with-lease")) or any(
        a.startswith("+") and len(a) > 1 for a in args
    )
    if sub == "push" and force_push:
        return "deny", "git push --force é proibido."
    if sub == "reset" and "--hard" in args:
        return "deny", "git reset --hard descarta trabalho."
    if sub == "clean" and has_flag(args, "f", ("--force",)):
        return "deny", "git clean -f apaga arquivos não rastreados."
    return None


def targets_protected_branch(ref: str) -> bool:
    """A referência de push (`main`, `HEAD:main`, `+main`, `refs/heads/main`) é a principal?"""
    name = ref.split(":")[-1].lstrip("+").removeprefix("refs/heads/")
    return name in PROTECTED_BRANCHES


def git_decision(tokens: list[str]) -> Decision | None:
    """Regras para os subcomandos perigosos do git em um segmento."""
    call = git_call(tokens)
    if call is None:
        return None
    sub, args = call
    if (blocked := destructive_git(sub, args)) is not None:
        return blocked
    if sub not in {"commit", "push"}:
        return None
    refs = [a for a in args if not a.startswith("-")]
    pushes_main = sub == "push" and any(targets_protected_branch(ref) for ref in refs)
    if common.current_branch() in PROTECTED_BRANCHES or pushes_main:
        return (
            "deny",
            "Commit/push direto na main é proibido: crie uma branch e abra PR.",
        )
    return "ask", "Commit/push só com autorização explícita do Patrick."


def rm_targets(tokens: list[str]) -> list[str]:
    """Alvos de um `rm` recursivo e forçado; vazio para qualquer outro comando."""
    effective, _ = effective_tokens(tokens)
    if not effective or Path(effective[0]).name != "rm":
        return []
    args = effective[1:]
    flags = "".join(a.lstrip("-") for a in args if a.startswith("-") and not a.startswith("--"))
    longs = {a for a in args if a.startswith("--")}
    recursive = "r" in flags.lower() or "--recursive" in longs
    forced = "f" in flags or "--force" in longs
    return [a for a in args if not a.startswith("-")] if recursive and forced else []


def is_broad_rm_target(target: str, cwd: Path | None) -> bool:
    """Alvo amplo demais: raiz, home, expansões, o projeto inteiro ou fora do projeto."""
    if target in BROAD_TARGETS or target.startswith("~") or re.search(r"[$`]", target):
        return True
    if cwd is None:
        return not Path(target).is_absolute()
    project = common.PROJECT_DIR.resolve()
    resolved = (cwd / target).resolve()
    if Path(target).is_absolute() and Path(tempfile.gettempdir()).resolve() in resolved.parents:
        return False
    if resolved in {project, project.parent} or project not in {
        resolved,
        *resolved.parents,
    }:
        return True
    return resolved.name in {".git", ".claude"} and resolved.parent == project


def next_cwd(tokens: list[str], cwd: Path | None) -> Path | None:
    """Diretório corrente após um segmento; `None` quando não dá para saber (`cd ~`, `cd $X`)."""
    if verb_of(tokens) != "cd":
        return cwd
    effective, _ = effective_tokens(tokens)
    target = effective[1] if len(effective) > 1 else "~"
    if cwd is None or target.startswith(("~", "-")) or re.search(r"[$`]", target):
        return None
    return (cwd / target).resolve()


def pip_decision(tokens: list[str], text: str) -> Decision | None:
    """`pip install` fora do venv do projeto e gerenciadores alternativos."""
    effective, _ = effective_tokens(tokens)
    verb = verb_of(tokens)
    words = set(effective[1:])
    is_pip = verb in {"pip", "pip3"} and "install" in effective[1:4]
    is_module = verb.startswith("python") and {"-m", "pip", "install"} <= words
    if is_pip or is_module:
        unsafe = bool({"--user", "--break-system-packages"} & words)
        in_venv = "backend/.venv" in text or bool(os.environ.get("VIRTUAL_ENV"))
        if unsafe or not in_venv:
            return "deny", PIP_HINT
    others = (
        verb == "poetry" and bool({"add", "install"} & words),
        verb == "pipenv" and "install" in words,
        verb in {"conda", "pipx"} and "install" in words,
        verb == "npm" and bool({"i", "install"} & words) and bool({"-g", "--global"} & words),
    )
    return (
        ("deny", "Gerenciador de pacotes fora do padrão (pip/npm do projeto).")
        if any(others)
        else None
    )


def scan_text(tokens: list[str]) -> str:
    """Texto do segmento sem os valores de `-m`, `--body`, `--title`, ... (mensagens livres)."""
    kept: list[str] = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
        elif token in MESSAGE_OPTS:
            skip = True
        else:
            kept.append(token)
    return " ".join(kept)


def destructive_misc(tokens: list[str], wrappers: set[str]) -> Decision | None:
    """`xargs rm` e `find ... -delete/-exec rm` pedem confirmação."""
    effective, _ = effective_tokens(tokens)
    verb = verb_of(tokens)
    if "xargs" in wrappers and verb == "rm":
        return "ask", "xargs rm: confirme os alvos."
    if verb == "find" and ("-delete" in effective or "rm" in effective):
        return "ask", "find com -delete/-exec rm: confirme os alvos."
    return None


def sensitive_decision(index: int, segments: list[Segment]) -> Decision | None:
    """Segredos, `.claude/state`, SQL destrutivo e `curl | sh` no segmento `index`."""
    tokens = segments[index][1]
    text = scan_text(tokens)
    verb = verb_of(tokens)
    if SECRET_RE.search(text) or KEY_FILE_RE.search(text):
        return (
            "deny",
            "Acesso a .env, chaves ou certificados é bloqueado; use .env.example.",
        )
    if verb in {"curl", "wget"} and index + 1 < len(segments):
        next_sep, next_tokens = segments[index + 1]
        if next_sep == "|" and verb_of(next_tokens) in SHELLS:
            return "deny", "Baixar e executar script (curl | sh) é proibido."
    if verb in DB_CLIENTS:
        piped = segments[index - 1][1] if index and segments[index][0] == "|" else []
        # falso positivo: regex que detecta DROP/TRUNCATE, sem LDAP
        # nosemgrep: skills.code-injection.skill-ldap-injection.skill-ldap-injection  # noqa: ERA001
        if SQL_RE.search(f"{scan_text(piped)} {text}"):
            return (
                "deny",
                "DROP/TRUNCATE de banco exige o Patrick executar manualmente.",
            )
    if STATE_RE.search(text) and (verb not in READ_ONLY_VERBS or WRITE_HINT_RE.search(text)):
        return "deny", STATE_MESSAGE
    return None


def nested_commands(tokens: list[str]) -> list[str]:
    """Comandos embutidos: `bash -c '...'`, `eval ...` e substituições `$(...)`/crases."""
    effective, _ = effective_tokens(tokens)
    nested = [m.group(1) or m.group(2) for m in SUBST_RE.finditer(" ".join(tokens))]
    if effective and Path(effective[0]).name in SHELLS and "-c" in effective:
        position = effective.index("-c") + 1
        nested += effective[position : position + 1]
    if effective and effective[0] == "eval":
        nested.append(" ".join(effective[1:]))
    return nested


def baseline_decision(tokens: list[str]) -> Decision | None:
    """Regravar as linhas de base do gate precisa de autorização."""
    if any(flag in tokens for flag in BASELINE_FLAGS):
        return (
            "ask",
            "Regravar a linha de base do gate esconde dívida: confirme com o Patrick.",
        )
    return None


def analyze(command: str, cwd: Path | None, depth: int = 0) -> list[Decision]:
    """Todas as decisões (deny/ask) para um comando, analisando os embutidos."""
    decisions: list[Decision] = []
    segments = parse_command(join_lines(command))
    for index, (_sep, tokens) in enumerate(segments):
        _, wrappers = effective_tokens(tokens)
        found = (
            sensitive_decision(index, segments)
            or git_decision(tokens)
            or pip_decision(tokens, scan_text(tokens))
            or baseline_decision(tokens)
            or destructive_misc(tokens, wrappers)
        )
        if any(is_broad_rm_target(t, cwd) for t in rm_targets(tokens)):
            found = "deny", "rm -rf em caminho amplo."
        if found:
            decisions.append(found)
        if depth < MAX_DEPTH:
            for inner in nested_commands(tokens):
                decisions += analyze(inner, cwd, depth + 1)
        cwd = next_cwd(tokens, cwd)
    return decisions


def decide(command: str, cwd: Path | None = None) -> Decision | None:
    """Decide sobre um comando Bash: `("deny"|"ask", motivo)` ou `None` para liberar."""
    decisions = analyze(command, cwd or common.PROJECT_DIR.resolve())
    denies = [d for d in decisions if d[0] == "deny"]
    asks = [d for d in decisions if d[0] == "ask"]
    if denies:
        return denies[0]
    return asks[0] if asks else None


def main() -> int:
    """Lê o comando do stdin e responde allow/ask/deny."""
    data = common.read_input()
    tool_input = data.get("tool_input")
    command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""
    raw_cwd = data.get("cwd")
    cwd = Path(str(raw_cwd)) if raw_cwd else None
    outcome = decide(command, cwd) if command else None
    if outcome:
        common.emit(common.pretool_decision(*outcome))
    return 0


if __name__ == "__main__":
    sys.exit(
        common.run_safely(
            main,
            "guard_bash",
            common.pretool_decision("ask", "Hook guard_bash falhou: confirme manualmente."),
        )
    )

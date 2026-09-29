"""Valida o design system: contraste WCAG AA dos tokens e uso de cores/fontes fora dos tokens.

Só usa a biblioteca padrão. Roda no gate (`scripts/quality_gate.py`) e nos hooks.

Uso:
    python scripts/check_design_tokens.py            # contraste + varredura de src/
    python scripts/check_design_tokens.py arq.tsx    # varredura só dos arquivos indicados
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
TOKENS_FILE = FRONTEND / "src" / "styles" / "tokens.css"
SCAN_SUFFIXES = {".ts", ".tsx", ".css", ".html", ".js"}
MAX_VAR_DEPTH = 5
SRGB_THRESHOLD = 0.03928
NON_TOKEN_FILES = {"tokens.css", "tailwind.config.js", "postcss.config.js"}

# (texto/componente, fundo, razão mínima, descrição). 4.5 = texto normal, 3.0 = texto grande/UI.
CONTRAST_PAIRS: tuple[tuple[str, str, float, str], ...] = (
    ("text-primary", "bg-page", 4.5, "texto principal na página"),
    ("text-primary", "bg-surface", 4.5, "texto principal em cartões"),
    ("text-secondary", "bg-page", 4.5, "texto secundário na página"),
    ("text-secondary", "bg-surface", 4.5, "texto secundário em cartões"),
    ("text-muted", "bg-page", 4.5, "texto discreto na página"),
    ("text-muted", "bg-surface", 4.5, "texto discreto em cartões"),
    ("text-link", "bg-page", 4.5, "link na página"),
    ("text-link", "bg-surface", 4.5, "link em cartões"),
    ("text-on-action", "action-primary", 4.5, "texto sobre ação primária"),
    ("text-on-action", "action-primary-hover", 4.5, "texto sobre ação primária (hover)"),
    ("text-on-action", "action-primary-active", 4.5, "texto sobre ação primária (active)"),
    ("text-on-header", "bg-header", 4.5, "texto no cabeçalho"),
    ("text-on-action", "action-secondary", 4.5, "texto sobre ação secundária"),
    ("accent-subtle-fg", "accent-subtle-bg", 4.5, "selo de destaque"),
    ("neutral-subtle-fg", "neutral-subtle-bg", 4.5, "selo neutro"),
    ("status-success-fg", "status-success-bg", 4.5, "status sucesso"),
    ("status-warning-fg", "status-warning-bg", 4.5, "status alerta"),
    ("status-error-fg", "status-error-bg", 4.5, "status erro"),
    ("status-info-fg", "status-info-bg", 4.5, "status info"),
    ("focus-ring", "bg-page", 3.0, "anel de foco na página"),
    ("focus-ring", "bg-surface", 3.0, "anel de foco em cartões"),
    ("border-strong", "bg-page", 3.0, "borda de campos"),
)

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
COLOR_FN_RE = re.compile(r"\b(?:rgb|rgba|hsl|hsla|oklch|oklab)\(")
FONT_RE = re.compile(r"font-family\s*:")
TW_PALETTE_RE = re.compile(
    r"\b(?:bg|text|border|ring|divide|from|to|via|fill|stroke|outline|decoration|shadow)-"
    r"(?:(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan"
    r"|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}|white|black)\b"
)
TW_LEGACY_RE = re.compile(r"\b(?:bg|text|border|ring|divide)-(?:lagoa|terracota|areia|grafite)\b")
OPACITY_TEXT_RE = re.compile(r"\bopacity-\d+\b")


@dataclass(frozen=True)
class Violation:
    """Ocorrência de cor ou fonte fora dos tokens."""

    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        """Formata como `arquivo:linha — mensagem`."""
        try:
            rel = self.path.relative_to(ROOT)
        except ValueError:
            rel = self.path
        return f"{rel}:{self.line} — {self.message}"


def parse_tokens(css: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Extrai o tema claro (`:root`) e as duas cópias do escuro.

    Returns:
        Claro, escuro forçado (`data-theme="dark"`) e escuro do sistema
        (`prefers-color-scheme`, dentro de `@media`).
    """
    targets: dict[str, dict[str, str]] = {
        ":root": {},
        ':root[data-theme="dark"]': {},
        ':root:not([data-theme="light"])': {},
    }
    decl = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")
    blocks = re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", css, flags=re.S))
    for raw_selector, body in blocks:
        target = targets.get(raw_selector.strip())
        if target is not None:
            target.update({name: value.strip() for name, value in decl.findall(body)})
    light, dark, dark_media = targets.values()
    return light, dark, dark_media


def resolve(name: str, values: dict[str, str], depth: int = 0) -> str:
    """Resolve `var(--x)` recursivamente até um hex."""
    value = values[name]
    match = re.fullmatch(r"var\((--[\w-]+)\)", value)
    if match and depth < MAX_VAR_DEPTH:
        return resolve(match.group(1), values, depth + 1)
    return value


def luminance(hex_color: str) -> float:
    """Luminância relativa WCAG de um hex `#rrggbb`."""
    digits = hex_color.lstrip("#")
    channels = [int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= SRGB_THRESHOLD else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_ratio(first: str, second: str) -> float:
    """Razão de contraste WCAG entre dois hex."""
    lum_a, lum_b = sorted((luminance(first), luminance(second)), reverse=True)
    return (lum_a + 0.05) / (lum_b + 0.05)


def check_contrast(css: str) -> list[str]:
    """Verifica todos os pares de `CONTRAST_PAIRS` nos temas claro e escuro."""
    light, dark, dark_media = parse_tokens(css)
    themes = {
        "claro": light,
        "escuro (data-theme)": {**light, **dark},
        "escuro (sistema)": {**light, **dark_media},
    }
    errors: list[str] = []
    if not dark_media:
        errors.append("bloco @media (prefers-color-scheme: dark) ausente ou vazio")
    for theme, values in themes.items():
        for fg, bg, minimum, label in CONTRAST_PAIRS:
            try:
                ratio = contrast_ratio(
                    resolve(f"--color-{fg}", values), resolve(f"--color-{bg}", values)
                )
            except KeyError as exc:
                errors.append(f"[{theme}] token ausente: {exc}")
                continue
            if ratio < minimum:
                errors.append(
                    f"[{theme}] {label}: {fg} sobre {bg} = {ratio:.2f}:1 (mínimo {minimum}:1)"
                )
    return errors


def scan_file(path: Path) -> list[Violation]:
    """Procura cores e fontes fora dos tokens num arquivo de interface."""
    if path.suffix not in SCAN_SUFFIXES or path.name in NON_TOKEN_FILES:
        return []
    violations: list[Violation] = []
    text = path.read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        if HEX_RE.search(line) or COLOR_FN_RE.search(line):
            violations.append(Violation(path, number, "cor literal; use um token semântico"))
        if FONT_RE.search(line):
            violations.append(Violation(path, number, "font-family fora dos tokens"))
        if TW_PALETTE_RE.search(line):
            violations.append(Violation(path, number, "cor da paleta padrão do Tailwind"))
        if TW_LEGACY_RE.search(line):
            violations.append(Violation(path, number, "classe de cor legada; use token semântico"))
        if OPACITY_TEXT_RE.search(line):
            violations.append(Violation(path, number, "opacity reduz contraste; use um token"))
    return violations


def default_targets() -> list[Path]:
    """Arquivos de interface do frontend (`src/` e `index.html`)."""
    files = [p for p in (FRONTEND / "src").rglob("*") if p.is_file()]
    files.append(FRONTEND / "index.html")
    return sorted(files)


def main(argv: list[str]) -> int:
    """Ponto de entrada: retorna 0 se tudo estiver conforme, 1 caso contrário."""
    problems: list[str] = []
    targets = [Path(a).resolve() for a in argv] if argv else default_targets()
    if not argv or TOKENS_FILE.resolve() in targets:
        problems.extend(check_contrast(TOKENS_FILE.read_text(encoding="utf-8")))
    for target in targets:
        problems.extend(str(v) for v in scan_file(target))
    if problems:
        lines = ["❌ design system:", *(f"  - {problem}" for problem in problems)]
        sys.stdout.write("\n".join(lines) + "\n")
        return 1
    sys.stdout.write("✅ design system: contraste AA e tokens em ordem\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

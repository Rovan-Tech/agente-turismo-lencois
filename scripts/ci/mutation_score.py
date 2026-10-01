"""Pontuação de mutação do backend a partir dos arquivos `.meta` que o mutmut grava.

Mutante morto = algum teste (ou o type check) notou a mudança. Só os códigos de saída que o mutmut
classifica como morto, timeout ou pego pelo type check contam (`mutmut/stats.py`); sobrevivente,
sem teste, pulado, suspeito e não executado ficam de fora. Sai com 1 se a pontuação ficar abaixo do
mínimo, para a qualidade dos testes nunca cair sem ninguém perceber.
"""

import argparse
import json
import sys
from pathlib import Path

_KILLED = frozenset({1, 3, 24, -24, 36, 37, 152, 255})


def count_mutants(meta_dir: Path) -> tuple[int, int]:
    """Devolve `(mortos, total)` somando todos os `.meta` sob `meta_dir`."""
    killed = total = 0
    for meta in sorted(meta_dir.rglob("*.meta")):
        codes = json.loads(meta.read_text(encoding="utf-8"))["exit_code_by_key"].values()
        total += len(codes)
        killed += sum(1 for code in codes if code in _KILLED)
    return killed, total


def main(argv: list[str]) -> int:
    """Imprime a pontuação e falha quando ela fica abaixo de `--min` (em %)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="backend/mutants", type=Path)
    parser.add_argument("--min", default=85.0, type=float)
    args = parser.parse_args(argv)

    killed, total = count_mutants(args.dir)
    if total == 0:
        sys.stderr.write(f"::error::Nenhum mutante encontrado em {args.dir}.\n")
        return 1
    score = 100 * killed / total
    sys.stdout.write(f"Pontuação de mutação: {killed}/{total} mortos ({score:.1f}%).\n")
    if score < args.min:
        sys.stderr.write(f"::error::Abaixo do mínimo de {args.min:.1f}%.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

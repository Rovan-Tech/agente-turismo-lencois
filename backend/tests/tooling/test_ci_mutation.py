import json
from pathlib import Path

import pytest

from tests.tooling.ci_helpers import load_ci_module

mutation_score = load_ci_module("mutation_score")


def _write_meta(directory: Path, name: str, codes: dict[str, int | None]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.meta").write_text(json.dumps({"exit_code_by_key": codes}))


def test_mutation_score_counts_only_mutants_a_test_caught(tmp_path):
    _write_meta(tmp_path / "app", "a.py", {"m1": 1, "m2": 1, "m3": 0, "m4": 33, "m5": None})
    _write_meta(tmp_path / "app", "b.py", {"m1": 1, "m2": 36})

    assert mutation_score.count_mutants(tmp_path) == (4, 7)


@pytest.mark.parametrize("code", [0, 2, 5, 33, 34, 35, None])
def test_mutation_score_does_not_count_statuses_that_are_not_a_kill(tmp_path, code):
    _write_meta(tmp_path, "a.py", {"m1": code})

    assert mutation_score.count_mutants(tmp_path) == (0, 1)


@pytest.mark.parametrize("code", [1, 3, 24, -24, 36, 37, 152, 255])
def test_mutation_score_counts_kills_timeouts_and_type_check_catches(tmp_path, code):
    _write_meta(tmp_path, "a.py", {"m1": code})

    assert mutation_score.count_mutants(tmp_path) == (1, 1)


def test_mutation_score_passes_at_the_minimum_and_fails_below_it(tmp_path, capsys):
    _write_meta(tmp_path, "a.py", {"m1": 1, "m2": 1, "m3": 1, "m4": 0})

    assert mutation_score.main(["--dir", str(tmp_path), "--min", "75"]) == 0
    assert "3/4 mortos (75.0%)" in capsys.readouterr().out
    assert mutation_score.main(["--dir", str(tmp_path), "--min", "75.1"]) == 1


def test_mutation_score_fails_when_there_are_no_mutants(tmp_path):
    assert mutation_score.main(["--dir", str(tmp_path)]) == 1

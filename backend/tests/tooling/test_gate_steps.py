import json
from collections import Counter
from pathlib import Path

import gate_steps as gs
import pytest
from gate_common import BACKEND, RunResult

SOURCE = "def busy(a):\n    if a:\n        return 1\n    return 2\n\n\nX = 1\n"


@pytest.fixture
def module(tmp_path):
    path = tmp_path / "mod.py"
    path.write_text(SOURCE, encoding="utf-8")
    return path.resolve()


def _ruff_json(path, code, row):
    finding = {
        "filename": str(path),
        "code": code,
        "message": "muito complexa",
        "location": {"row": row, "column": 1},
        "end_location": {"row": row, "column": 5},
    }
    return RunResult(1, json.dumps([finding]))


def test_function_span_returns_whole_function(module):
    assert gs.function_span(module, 1) == (1, 4)


def test_function_span_falls_back_to_row_when_not_a_function(module):
    assert gs.function_span(module, 7) == (7, 7)


@pytest.mark.parametrize(
    ("changed_line", "expected_ok"),
    [(3, False), (7, True)],
    ids=["body-changed", "other-part-of-file-changed"],
)
def test_lint_diff_function_level_rules_cover_the_whole_function(
    monkeypatch, module, changed_line, expected_ok
):
    monkeypatch.setattr(gs, "run", lambda *_a, **_k: _ruff_json(module, "C901", 1))

    result = gs.lint_diff([module], {module: frozenset({changed_line})})

    assert result.ok is expected_ok


def test_lint_diff_line_level_rules_stay_on_their_own_line(monkeypatch, module):
    monkeypatch.setattr(gs, "run", lambda *_a, **_k: _ruff_json(module, "D103", 1))

    assert gs.lint_diff([module], {module: frozenset({3})}).ok is True
    assert gs.lint_diff([module], {module: frozenset({1})}).ok is False


def test_parse_mypy_extracts_file_line_message_and_code(tmp_path):
    out = 'app/x.py:12: error: Missing type arguments for generic type "dict"  [type-arg]\n'

    [(path, line, msg, code)] = gs.parse_mypy(tmp_path, out)

    assert path == (tmp_path / "app/x.py").resolve()
    assert (line, code) == (12, "type-arg")
    assert msg.startswith("Missing type arguments")


def test_run_mypy_fails_loudly_when_mypy_is_missing(monkeypatch):
    missing = RunResult(1, "/usr/bin/python3: No module named mypy")
    monkeypatch.setattr(gs, "run", lambda *_a, **_k: missing)

    with pytest.raises(gs.MypyRunError):
        gs.run_mypy([BACKEND / "app" / "main.py"])


def test_types_python_reports_missing_mypy_as_failure(monkeypatch):
    missing = RunResult(1, "No module named mypy")
    monkeypatch.setattr(gs, "run", lambda *_a, **_k: missing)

    result = gs.types_python([BACKEND / "app" / "main.py"], {})

    assert result.ok is False
    assert "mypy não executou" in result.detail[0]


def _fake_mypy(monkeypatch, path, baseline):
    monkeypatch.setattr(gs, "run_mypy", lambda _files: [(BACKEND, [(path, 5, "erro x", "code")])])
    monkeypatch.setattr(gs, "load_mypy_baseline", lambda: Counter(baseline))


def test_types_python_accepts_known_baseline_errors_on_untouched_lines(monkeypatch):
    path = BACKEND / "app" / "legado.py"
    _fake_mypy(monkeypatch, path, {gs.mypy_key(path, "code", "erro x"): 1})

    assert gs.types_python([path], {path: frozenset({99})}).ok is True


def test_types_python_fails_on_new_error_even_in_untouched_file(monkeypatch):
    path = BACKEND / "app" / "legado.py"
    _fake_mypy(monkeypatch, path, {})

    assert gs.types_python([path], {}).ok is False


def test_types_python_fails_on_baseline_error_in_changed_line(monkeypatch):
    path = BACKEND / "app" / "legado.py"
    _fake_mypy(monkeypatch, path, {gs.mypy_key(path, "code", "erro x"): 1})

    assert gs.types_python([path], {path: frozenset({5})}).ok is False


def test_mypy_baseline_file_lists_current_legacy_errors():
    baseline = json.loads(Path(gs.MYPY_BASELINE).read_text(encoding="utf-8"))

    assert sum(baseline.values()) == 16

from pathlib import Path

import gate_common as gc
import pytest

DIFF = """\
diff --git a/backend/app/a.py b/backend/app/a.py
+++ b/backend/app/a.py
@@ -1,2 +3,2 @@
@@ -10 +20 @@
diff --git a/x b/x
+++ /dev/null
@@ -1 +1 @@
"""


def test_parse_diff_collects_new_lines_per_file():
    result = gc.parse_diff(DIFF)

    assert result == {(gc.ROOT / "backend/app/a.py").resolve(): frozenset({3, 4, 20})}


def test_parse_diff_ignores_deleted_files():
    diff = "+++ /dev/null\n@@ -1 +0,0 @@\n"

    assert gc.parse_diff(diff) == {}


@pytest.mark.parametrize(
    ("lines", "start", "end", "expected"),
    [
        (None, 1, 2, True),
        (frozenset({5}), 4, 6, True),
        (frozenset({5}), 6, 9, False),
        (frozenset(), 1, 100, False),
        (frozenset({7}), 7, None, True),
    ],
)
def test_touches_checks_overlap(lines, start, end, expected):
    assert gc.touches(lines, start, end) is expected


def test_is_python_source_accepts_backend_scripts_and_hooks_only():
    root = gc.ROOT

    assert gc.is_python_source(root / "backend/app/main.py")
    assert gc.is_python_source(root / "scripts/quality_gate.py")
    assert gc.is_python_source(root / ".claude/hooks/guard_bash.py")
    assert not gc.is_python_source(root / "frontend/x.py")
    assert not gc.is_python_source(root / "backend/README.md")


def test_run_reports_missing_command():
    result = gc.run(["comando-que-nao-existe-xyz"], cwd=Path())

    assert result.returncode == gc.COMMAND_NOT_FOUND

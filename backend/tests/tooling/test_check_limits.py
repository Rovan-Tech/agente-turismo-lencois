from pathlib import Path

import check_limits as cl


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "mod.py"
    path.write_text(body, encoding="utf-8")
    return path


def test_find_violations_flags_long_function(tmp_path):
    body = "def big():\n" + "    x = 1\n" * 45

    violations = cl.find_violations(_write(tmp_path, body))

    assert [v.message.split(":")[0] for v in violations] == ["big"]


def test_find_violations_ignores_docstring_lines(tmp_path):
    doc = '    """' + "linha\n" * 60 + '    """\n'
    body = "def documented():\n" + doc + "    return 1\n"

    assert cl.find_violations(_write(tmp_path, body)) == []


def test_find_violations_flags_deep_nesting(tmp_path):
    body = (
        "def deep(a):\n"
        "    if a:\n        for i in a:\n            while i:\n                if i:\n"
        "                    return i\n"
    )

    violations = cl.find_violations(_write(tmp_path, body))

    assert any("aninhamento 4" in v.message for v in violations)


def test_find_violations_accepts_three_levels(tmp_path):
    body = (
        "def ok(a):\n    if a:\n        for i in a:\n            if i:\n                return i\n"
    )

    assert cl.find_violations(_write(tmp_path, body)) == []


def test_find_violations_flags_large_module(tmp_path):
    body = "x = 1\n" * (cl.MAX_MODULE_LINES + 1)

    violations = cl.find_violations(_write(tmp_path, body))

    assert violations[0].message.startswith("módulo com")


def test_find_violations_does_not_count_elif_as_extra_nesting(tmp_path):
    body = (
        "def choose(a):\n"
        "    for i in a:\n"
        "        if i == 1:\n            return 1\n"
        "        elif i == 2:\n            return 2\n"
        "        elif i == 3:\n            return 3\n"
    )

    assert cl.find_violations(_write(tmp_path, body)) == []

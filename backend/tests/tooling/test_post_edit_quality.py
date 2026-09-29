import hook_common as common
import post_edit_quality as pq
import pytest


@pytest.mark.parametrize(
    ("rel", "line"),
    [
        ("backend/app/x.py", "x = 1  # type: ignore"),
        ("backend/app/x.py", "import os  # noqa"),
        ("backend/tests/test_x.py", "@pytest.mark.skip(reason='x')"),
        ("backend/app/x.py", "    print('debug')"),
        ("backend/app/x.py", "    except:"),
        ("backend/app/x.py", "    except ValueError: pass"),
        ("backend/app/x.py", "    breakpoint()"),
        ("backend/app/x.py", 'API_KEY = "gsk_abcdefghijklmnopqrstuvwxyz123456"'),
        ("frontend/src/a.ts", "// @ts-ignore"),
        ("frontend/tests/a.test.ts", "it.skip('x', () => {})"),
        ("frontend/src/a.tsx", "console.log(phone)"),
    ],
)
def test_scan_anti_patterns_flags_workarounds(rel, line):
    assert len(pq.scan_anti_patterns(rel, [(3, line)])) == 1


@pytest.mark.parametrize(
    ("rel", "line"),
    [
        ("backend/app/x.py", "x = 1  # type: ignore[arg-type]  # lib sem stubs"),
        ("backend/app/x.py", "import os  # noqa: F401  # reexport"),
        ("backend/app/x.py", "logger.info('ok')"),
        ("backend/app/x.py", "token = settings.dashboard_api_token"),
        ("frontend/src/a.ts", "// @ts-expect-error justificado"),
    ],
)
def test_scan_anti_patterns_accepts_justified_code(rel, line):
    assert pq.scan_anti_patterns(rel, [(1, line)]) == []


def test_scan_anti_patterns_skips_hook_sources():
    assert pq.scan_anti_patterns(".claude/hooks/x.py", [(1, "print('x')")]) == []


def test_main_ignores_files_outside_project(monkeypatch):
    monkeypatch.setattr(common, "read_input", lambda: {"tool_input": {"file_path": "/etc/hosts"}})

    assert pq.main() == 0

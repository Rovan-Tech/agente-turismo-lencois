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
        ("frontend/src/a.tsx", "console.debug(payload)"),
        ("frontend/src/a.ts", "const data: any = await res.json();"),
        ("frontend/src/a.ts", "const data = body as any;"),
        ("frontend/src/a.tsx", "<div dangerouslySetInnerHTML={{ __html: text }} />"),
        ("frontend/src/a.ts", "localStorage.setItem('access_token', token);"),
        ("frontend/src/a.ts", 'sessionStorage.getItem("jwt")'),
        ("backend/app/x.py", "def f(payload: Any) -> None:"),
        ("backend/app/x.py", "data: dict[str, Any] = {}"),
        ("backend/app/x.py", "    model_config = ConfigDict(extra='allow')"),
        ("backend/app/x.py", 'app.add_middleware(CORSMiddleware, allow_origins=["*"])'),
        ("backend/app/x.py", "@app.on_event('startup')"),
        ("frontend/src/a.ts", "const r: Record<string, any> = {};"),
        ("frontend/src/a.ts", "function f<T = any>(x: T) {}"),
        ("backend/app/x.py", 'y: Any = "#1"'),
        ("frontend/src/a.ts", 'localStorage.setItem("authorization", jwt);'),
        ("frontend/src/a.ts", 'localStorage.setItem("authToken", jwt);'),
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
        ("frontend/src/lib/theme.ts", 'window.localStorage.setItem("theme", theme);'),
        ("frontend/src/a.ts", "const data: unknown = await res.json();"),
        ("frontend/src/a.ts", "const company = 1; // many"),
        ("frontend/src/a.ts", "console.error(error);"),
        ("backend/app/x.py", "data: dict[str, Any] = {}  # payload JSON da Meta"),
        ("backend/app/x.py", "from typing import Any"),
        ("backend/app/x.py", "    model_config = ConfigDict(extra='forbid')"),
        ("backend/app/x.py", 'SYSTEM = "Rules: Any question about tours is welcome."'),
        ("frontend/src/a.ts", 'localStorage.setItem("author", name);'),
    ],
)
def test_scan_anti_patterns_accepts_justified_code(rel, line):
    assert pq.scan_anti_patterns(rel, [(1, line)]) == []


def test_scan_anti_patterns_skips_hook_sources():
    assert pq.scan_anti_patterns(".claude/hooks/x.py", [(1, "print('x')")]) == []


def test_main_ignores_files_outside_project(monkeypatch):
    monkeypatch.setattr(common, "read_input", lambda: {"tool_input": {"file_path": "/etc/hosts"}})

    assert pq.main() == 0

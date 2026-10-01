import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import checklist
import hook_common as common
import pytest
import record_verdict as rv

from tests.tooling.ci_helpers import executable, git, run_script

CHECKLIST_TABLE = (
    "| ID | Controle | Requisito | Hoje | Dono | N/A |\n"
    "|---|---|---|---|---|---|\n"
    "| GOV-1 | ADR | x | — | reviewer | o diff não altera arquitetura |\n"
    "| GIT-1 | Git | x | — | reviewer | o diff não cria arquivos |\n"
    "| GATE-2 | Gate | x | — | qa | o diff não muda código |\n"
)


@pytest.fixture
def state(tmp_path, monkeypatch):
    """Diretórios de estado e relatórios isolados, com fingerprint fixo."""
    monkeypatch.setattr(common, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(common, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(rv, "VERDICTS_FILE", tmp_path / "state" / "verdicts.json")
    monkeypatch.setattr(common, "STARTS_FILE", tmp_path / "state" / "starts.json")
    monkeypatch.setattr(common, "fingerprint", lambda: ("fp2", ["backend/app/a.py"]))
    return tmp_path


@pytest.fixture
def fake_checklist(tmp_path, monkeypatch):
    """Checklist pequeno e estável, independente do conteúdo real de `docs/`."""
    table = tmp_path / "checklist-engenharia.md"
    table.write_text(CHECKLIST_TABLE, encoding="utf-8")
    monkeypatch.setattr(checklist, "CHECKLIST_FILE", table)


# --- fixtures dos testes de scripts/ci --------------------------------------------------------


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "ci@example.com")
    git(tmp_path, "config", "user.name", "CI")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("a")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


@pytest.fixture
def fake_api():
    """Servidor HTTP mínimo que imita a API: /health aberto, /api/* exige o token certo."""
    state = {
        "health_body": {"status": "ok"},
        "token": "segredo",
        "tours": [{"id": "x"}],
        "open": False,
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def _send(self, status, body):
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):  # noqa: N802  # nome exigido pelo BaseHTTPRequestHandler
            if self.path == "/health":
                return self._send(200, state["health_body"])
            if (
                not state["open"]
                and self.headers.get("Authorization") != f"Bearer {state['token']}"
            ):
                return self._send(401, {"detail": "não autorizado"})
            return self._send(200, state["tours"])

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state["url"] = f"http://127.0.0.1:{server.server_address[1]}"
    yield state
    server.shutdown()


@pytest.fixture
def deploy_env(tmp_path):
    """`gcloud` e teste de fumaça falsos que registram como foram chamados."""
    log = tmp_path / "calls.log"
    gcloud = executable(tmp_path / "gcloud", f'echo "gcloud $*" >> "{log}"\n')
    counter = tmp_path / "counter"
    counter.write_text("0")

    def make_smoke(*, fail_first: int) -> Path:
        return executable(
            tmp_path / "smoke",
            f'n=$(cat "{counter}"); echo $((n + 1)) > "{counter}"\n'
            f'echo "smoke $*" >> "{log}"\n'
            f'[ "$n" -ge {fail_first} ]\n',
        )

    def run(smoke, *args):
        return run_script(
            "verify_deploy.sh",
            *args,
            env={
                "GCLOUD_BIN": str(gcloud),
                "SMOKE_SCRIPT": str(smoke),
                "VERIFY_ATTEMPTS": "3",
                "VERIFY_DELAY": "0",
            },
        )

    return log, make_smoke, run

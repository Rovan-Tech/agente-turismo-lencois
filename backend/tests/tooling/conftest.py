import checklist
import hook_common as common
import pytest
import record_verdict as rv

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

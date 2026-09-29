# Atalhos do gate de qualidade (a lógica vive em scripts/quality_gate.py).
VENV_PYTHON := backend/.venv/bin/python
PYTHON = $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),python3)

.PHONY: gate-fast gate setup

gate-fast:
	$(PYTHON) scripts/quality_gate.py --fast

gate:
	$(PYTHON) scripts/quality_gate.py --full

setup:
	python3 -m venv backend/.venv
	$(VENV_PYTHON) -m pip install -r backend/requirements-dev.txt
	cd frontend && npm ci && npx playwright install chromium

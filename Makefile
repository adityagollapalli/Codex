PYTHON ?= python

.PHONY: install run test lint typecheck format

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt

install-ai:
	$(PYTHON) -m pip install -r requirements-ai.txt

run:
	$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy app tests

format:
	$(PYTHON) -m ruff format .

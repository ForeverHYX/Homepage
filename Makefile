PYTHON ?= python3
VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
HOST ?= 127.0.0.1
PORT ?= 8000
URL ?= http://$(HOST):$(PORT)

.PHONY: setup build run format lint test check doctor password profile

setup:
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PY) scripts/build_frontend.py
	$(PY) scripts/doctor.py --check-build

build:
	$(PY) scripts/build_frontend.py

run:
	$(PY) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

format:
	$(PY) -m ruff format app scripts tests

lint:
	$(PY) -m ruff format --check app scripts tests
	$(PY) -m ruff check app scripts tests

test:
	$(PY) -m pytest -q

check:
	$(PY) scripts/build_frontend.py --check
	$(PY) -m ruff format --check app scripts tests
	$(PY) -m ruff check app scripts tests
	$(PY) -m pytest -q

doctor:
	$(PY) scripts/doctor.py --check-build

password:
	$(PY) scripts/hash_password.py

profile:
	$(PY) scripts/profile_frontend.py $(URL)

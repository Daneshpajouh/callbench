# Common tasks. Run `make help` for the list.
VENV ?= .venv
PY := $(VENV)/bin/python
SMK := $(PY) tools/snakemake_macos.py
CORES ?= 8

.PHONY: help venv lint format test test-workflow run report dag data test-data clean

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

venv: ## create .venv with Snakemake and the dev tools
	python3 -m venv $(VENV) && $(VENV)/bin/pip install -r requirements-dev.txt

lint: ## snakemake --lint, snakefmt --check, ruff, mypy, shellcheck
	$(VENV)/bin/snakemake --lint
	$(VENV)/bin/snakefmt --check workflow
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .
	$(VENV)/bin/mypy
	shellcheck tools/*.sh

format: ## apply snakefmt and ruff format
	$(VENV)/bin/snakefmt workflow
	$(VENV)/bin/ruff format .

test: ## unit tests for the scripts, then dry-run and lint tests
	$(PY) -m pytest -q tests/unit
	$(PY) -m pytest -q -m workflow tests/workflow

test-workflow: ## end-to-end run on the bundled HG002 slice, then the accuracy check
	nice -n 10 $(SMK) --profile profiles/test
	$(PY) tools/check_accuracy.py .tests/integration/results/report/accuracy.tsv .tests/expected_accuracy.tsv

data: ## fetch the public full-size inputs into resources/full (see docs/data_sources.md)
	tools/fetch_public_data.sh resources/full

test-data: ## rebuild .tests/data from a finished full-size run
	tools/make_test_data.sh results resources/full

run: ## full-size run with the local profile
	nice -n 10 $(SMK) --profile profiles/local --cores $(CORES)

report: ## self-contained HTML report of the last full-size run
	$(VENV)/bin/snakemake --profile profiles/local --report results/report.html

dag: ## rule graph as SVG (needs graphviz)
	$(VENV)/bin/snakemake --rulegraph | dot -Tsvg > docs/images/rulegraph.svg

clean: ## remove results, logs and benchmarks of the full-size run
	rm -rf results logs benchmarks

# Contributing

callbench has one maintainer. This file says how to run the checks and how to report a problem.

## Run the checks

```
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pre-commit install
make lint
make test
make test-workflow
```

`pre-commit install` adds the hooks in `.pre-commit-config.yaml`, including a 5000 kB limit on added files. `make lint` runs `snakemake --lint`, `snakefmt --check`, `ruff check`, `ruff format --check`, mypy and shellcheck; shellcheck is not a Python package, so install it with your system's package manager. `make test` runs the pytest suite. `make test-workflow` runs every rule on the bundled HG002 slice and needs conda or mamba on your `PATH`. If a check cannot run on your machine, say which one and why in the pull request. If a change moves any number in the benchmark table, say by how much and why. Do not commit data files over 5 MB, credentials or tokens.

## Report a problem

Open an issue with the bug report form and fill in every required field. To propose a caller, use the new caller form; `docs/evaluation/caller_evaluation.md` says what evidence it needs.

## Versions and releases

Versions follow semantic versioning on the output contract and the config schema:

- MAJOR: a path, file format, column or config key that users read is removed, renamed or retyped, or a key becomes required.
- MINOR: a new caller, rule or report section that leaves existing outputs and configuration valid.
- PATCH: fixes.

Each change adds a line to `CHANGELOG.md` under `Unreleased`. A release moves those lines under a dated heading such as `## [1.0.0] - 2026-10-19`, sets `version` and `date-released` in `CITATION.cff` and `version` in `.zenodo.json`, and tags the merge commit on `main` as `vMAJOR.MINOR.PATCH`. Pushing the tag runs `.github/workflows/release.yml`. It publishes nothing until the tag matches both version fields, the changelog has a section for it, and the CI checks and the integration test inside the new image pass.

Contributions are licensed under the Apache License 2.0 that covers this repository.

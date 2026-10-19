# Contributing

germline-benchmark-smk is a Snakemake workflow that calls germline small variants from short reads with bcftools and FreeBayes, and benchmarks the calls against the Genome in a Bottle HG002 v4.2.1 truth set with RTG vcfeval. This file explains how to set up a development environment, what a change must pass before review, how to add a caller, and how versions are numbered.

For anything larger than a small fix, open an issue first. The issue forms (bug report, feature request, new caller) ask for the details a reviewer needs, and they let us agree on the effect on the output contract before you write code.

By submitting a contribution you agree that it is licensed under the Apache License 2.0 that covers this repository (section 5 of the licence).

## Set up

The workflow is developed and tested with Snakemake 9.27. Rule software environments are built by Snakemake from the files in `workflow/envs/`, so conda or mamba must be on your `PATH` to run the workflow itself.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pre-commit install
```

`pre-commit install` registers the hooks in `.pre-commit-config.yaml`: YAML syntax, end-of-file and trailing-whitespace fixes, a 5000 kB limit on added files, ruff, snakefmt and shellcheck. To run them on the whole tree, use `.venv/bin/pre-commit run --all-files`.

Public inputs are fetched with `tools/fetch_public_data.sh` and are not stored in the repository. Do not commit data files over 5 MB, credentials or tokens.

## Branches

Branch from `develop` and open the pull request against `develop`. `main` only moves on a release: a `release/vX.Y.Z` branch is cut from `develop`, gets its CHANGELOG section and version bumps, and is merged to `main` and tagged `vX.Y.Z`. Name working branches for the kind of change:

- `feature/<short-description>` for new behaviour, such as a caller, a rule or a report section (for example `feature/add-stratification-summary`).
- `fix/<short-description>` for bug fixes (for example `fix/chunk-boundary-overlap`).

Use lower case and hyphens. Keep each branch to one logical change.

## Commits

Write the subject line in the imperative mood and keep it under 72 characters, with no trailing full stop. "Add FreeBayes chunk merge rule" is correct; "Added" and "Adds" are not. Use the body, wrapped at 72 characters, to explain why the change is needed and what you checked. Reference the issue in the body (for example `Refs #12`). Make one logical change per commit.

## Checks before review

Run these three commands from the repository root. A change is ready for review when all of them pass.

```
make lint
make test
make test-workflow
```

- `make lint` runs the static checks: `snakemake --lint`, `snakefmt --check`, ruff and mypy.
- `make test` runs the pytest suite.
- `make test-workflow` runs the workflow end to end with the `test` profile.

Tick the matching boxes in the pull request template. If a check cannot run on your machine, say which one and why in the pull request instead of ticking it.

If your change moves any number in the benchmark table, explain by how much and why in the pull request. A reviewer should not have to diff the tables to find out.

## Adding a caller

1. Open an issue with the "new caller" form. It asks for the caller name and version, its licence, a container image with digest, the bioconda package, the platforms it runs on, and the evidence described below.
2. Read `docs/evaluation/caller_evaluation.md`. It describes how callers are evaluated and what a reviewer needs to see before a caller is accepted.
3. Add the rule under `workflow/rules/` and the software environment under `workflow/envs/`, with exact versions pinned. If the caller adds configuration keys, describe them in the schema under `workflow/schemas/`.
4. Meet the output contract. The caller must:
   - write a bgzipped, indexed VCF for each scatter chunk at `results/calls/{sample}/{caller}/chunks/{chunk}.vcf.gz`;
   - write a single sample column, named as the sample;
   - include the GT field;
   - pass the normalisation rule;
   - have its runtime and memory captured by the `benchmark` directive of the calling rule.
5. Include the evidence in the pull request: vcfeval precision, recall and F1 for SNVs and indels on HG002 against the current default caller, plus peak memory and runtime.
6. Update the documentation and add a CHANGELOG entry. A new caller is a MINOR release.

## Versioning

The workflow follows semantic versioning, applied to its output contract and its config schema:

- MAJOR: a breaking change to the output contract (paths, file formats or columns that downstream users read) or to the config schema (a key removed, renamed, retyped or newly required).
- MINOR: a new caller, rule or report section that leaves existing outputs and configuration valid.
- PATCH: fixes.

If a change does not fit one of these cleanly, ask in the issue. The maintainer decides the level before the change is merged.

## Changelog

Every change adds an entry to `CHANGELOG.md` under `Unreleased`, in the same pull request. Group entries under Added, Changed, Fixed or Removed, write one line per change, and give the issue number. For a MAJOR change, say what users must change in their configuration or downstream scripts.

Released sections use the heading `## [1.0.0] - 2026-10-19` (version, then the release date in ISO format). The release workflow reads the section whose heading matches the tag and uses it as the release notes.

## Releases

Maintainers release in this order:

1. Move the `Unreleased` entries under a new dated heading in `CHANGELOG.md`.
2. Set `version` and `date-released` in `CITATION.cff`, and `version` in `.zenodo.json`.
3. Merge to `main`, then tag the merge commit `vMAJOR.MINOR.PATCH` and push the tag.

Pushing the tag runs `.github/workflows/release.yml`. It stops if the tag does not match the version in `CITATION.cff` or `.zenodo.json`, or if the changelog has no section for that version. Otherwise it creates the GitHub release.

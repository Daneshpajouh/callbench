# Testing

Four layers, cheapest first. Each catches a different kind of fault; a change
is ready for review when all four pass.

| Layer | Command | Run time here | What it catches |
| --- | --- | --- | --- |
| Unit | `make test` | 3.7 s, 349 tests | Logic errors in the Python scripts: interval arithmetic, metric definitions, parsing of fastp, samtools, mosdepth and benchmark files, error messages |
| Workflow static | `.venv/bin/python -m pytest -m workflow tests/workflow` | 3.2 s, 3 tests | Broken DAG (dry run of the full config), `snakemake --lint` findings, unformatted Snakefiles |
| End to end | `make test-workflow` | 29 to 48 s warm, 102 s with first-time conda builds | Rules that do not connect, wrong tool flags, environment solver conflicts, temp files deleted too early |
| Validation | full run, then `docs/validation.md` | 212 s | Accuracy against GIAB truth; regressions after a caller, parameter or reference change |

## Unit tests

`tests/unit/`, one file per script, parametrised over edge cases taken from
real inputs: a header-only VCF, a multi-allelic site, a data line with the
wrong column count, an INFO field of `.`, BEDs with and without the `chr`
prefix, an empty BED, CRLF line endings, gzip and plain copies of the same
BED, benchmark files with `NA` (as Snakemake writes them on macOS without the
psutil shim), and an empty ClinVar table. The fixtures are hand-written, a few
lines each, under `tests/data/`; `tests/data/README.md` lists what each one
exercises and which test uses it, and `test_fixtures.py` checks that each
file still has that property.

Coverage from the run on 2026-10-19 on the v1.0.2 tree
(`.venv/bin/python -m pytest -q --cov=workflow/scripts --cov=tools tests/unit`):
367 passed; 587 statements, 1 missed, 99%. Every script is at 100% except
`runlog.py` (66 of 67 statements, shown as 99%).

The same suite was run from a fresh clone in a `python:3.12-slim` Linux
container (`pip install -r requirements-dev.txt`, then the commands above):
332 passed and 17 skipped (the tests that call bcftools, which the image does
not have); the workflow layer gave 2 passed and 1 skipped (the dry run, which
needs the full-size data). The first container run failed one test: the run
manifest called `git`, which the slim image lacks. `runlog.git_state` now
records no commit in that case, with a test.

Writing these tests found five bugs, each fixed in the same change: an empty
stratum BED made `bcftools view -T` fail instead of counting zero; an empty
list of ClinVar tables crashed `pd.concat`; `cpu_s_total` showed 0.0 instead
of NA when no job had CPU data; a figure panel with no F1 values (no indels in
a small slice) raised in matplotlib; and an F1 drop of exactly the tolerance
was flagged by float rounding.

## Workflow static tests

`tests/workflow/test_dry_run.py` runs `snakemake -n` on `config/config.yaml`
(skipped when the full-size data is not present) and checks that `bwa_mem`
and `vcfeval` are scheduled. It found a real bug: `unpack()` of a checkpoint
input function left `gather_calls` without a named input during a dry run.
`test_lint.py` runs `snakemake --lint` and `snakefmt --check`. These tests
are marked `workflow` and deselected by plain `pytest`.

## End to end

`profiles/test` runs every rule on a 200 kb slice of chr17 around BRCA1
(19,856 HG002 read pairs, 5.5 MB in `.tests/integration/data/`, built by
`tools/make_test_data.sh`). `tools/check_accuracy.py` then compares the
accuracy table with `.tests/expected_accuracy.tsv` and fails when any F1
drops by more than 0.005. On the slice both callers find all 55 truth SNVs and
15 truth indels with no false positives, so the check is strict: any lost
variant fails it.

Snakemake's `--generate-unit-tests` was tried on this run. It produced 28
per-rule tests and copied 47 MB of inputs and expected outputs; with the
test data outside the working directory the sampled tests could not find
their inputs, and after moving the data inside, a run of all 28 did not
finish within 290 s on this machine. They are not shipped in v1.0.0; making
them small and fast is part of milestone M1 in `ROADMAP.md`.

## Validation

The top layer is the full-size HG002 run compared with GIAB v4.2.1 truth,
reported in `docs/validation.md`. Rerun it after any change to a caller,
its parameters, the filters, the reference or the truth set, and compare the
`all` rows: a drop of more than 0.005 in F1 needs an explanation in the pull
request.

## CI

`.github/workflows/ci.yml` runs the unit and workflow static tests on
`ubuntu-latest` and `macos-latest`, then the end-to-end test and the accuracy
check on `ubuntu-latest`. The repository has not been pushed, so CI has not
run yet; the commands it runs are the ones above, which passed locally.

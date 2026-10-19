# germline-benchmark-smk

A Snakemake workflow that finds small inherited DNA variants in short-read
sequencing data and measures how often it gets them right, using reference
genomes whose true variants are already known.

## What this is for

Everyone carries a few million small differences from the human reference
genome: single-letter changes (SNVs) and short insertions or deletions
(indels). A few of them, in genes such as BRCA1 and BRCA2, change a person's
cancer risk and their care. Finding them from sequencing reads is called
germline variant calling, and the software that does it (a "caller") makes
mistakes: it misses real variants (false negatives) and reports variants that
are not there (false positives).

The Genome in a Bottle consortium (GIAB) publishes reference samples, such as
HG002, whose variants have been worked out with many technologies. Running a
pipeline on HG002 and comparing its output with the GIAB answer key gives
precision (how many reported variants are real), recall (how many real
variants were found) and their combination, F1. Doing this per region type
(easy sequence, repeats, duplicated sequence) shows where a pipeline is
weak. A clinical lab validates its pipeline this way before reporting on
patients, and again after every software change.

This workflow does that for two callers, bcftools and FreeBayes, on HG002
reads around BRCA1 and BRCA2, and reports accuracy, runtime and memory side by
side.

## Results (v1.0.0, HG002, 3.8 Mb around BRCA1 and BRCA2)

| Caller | SNV recall | SNV precision | SNV F1 | Indel recall | Indel precision | Indel F1 |
| --- | --- | --- | --- | --- | --- | --- |
| bcftools 1.23.1 | 0.9965 | 0.9979 | 0.9972 | 0.9117 | 0.9254 | 0.9185 |
| FreeBayes 1.3.10 | 0.9953 | 0.9951 | 0.9952 | 0.9087 | 0.9560 | 0.9318 |

3,412 truth SNVs and 657 truth indels inside the GIAB confident regions; about
29x mean depth. Per-stratum numbers, runtime and memory are in
`docs/validation.md`; the deployment recommendation is in
`docs/evaluation/caller_evaluation.md`. These numbers describe two 2 Mb windows
picked for their genes, not the whole genome.

## Quick start (about 5 minutes, bundled test data)

Needs Python 3.12 or later and conda 24.7.1 or later on `PATH`.

```
git clone https://github.com/Daneshpajouh/germline-benchmark-smk
cd germline-benchmark-smk
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
make test-workflow
```

`make test-workflow` builds the conda environments on first use, then runs
the whole pipeline on a 200 kb slice of chr17 around BRCA1 (19,856 HG002
read pairs, 6 MB in `.tests/data/`). Results land in
`.tests/integration/results/`; the accuracy table is
`.tests/integration/results/report/accuracy.tsv`.

## Running on real data

```
make data          # region fetch of the public inputs, about 800 MB
make run           # full run, 8 cores
make report        # results/report.html
```

On a Slurm cluster, set `slurm_account` and `slurm_partition` in
`profiles/slurm/config.v8+.yaml` and run
`.venv/bin/snakemake --profile profiles/slurm`. The step-by-step procedure,
including checks before and after a run, is `docs/sop.md`.

## How it works

```
FASTQ -> fastp -> bwa mem | fixmate | sort -> markdup -> samtools stats, mosdepth
                                                |
                     scatter_intervals (checkpoint: chunks of <= 500 kb)
                                                |
                       bcftools  |  FreeBayes   (one job per chunk)
                                                |
                    gather -> normalise -> vcfeval vs GIAB v4.2.1 -> strata
                                         \-> ClinVar annotation
                                                |
                  accuracy, QC, profiling tables -> snakemake --report
```

Software comes from pinned per-rule conda environments in `workflow/envs/`.
Each heavy rule has a `benchmark` directive; `results/report/profiling.tsv`
collects them. Memory and runtime requests are functions of input size and
grow on retry. The config and samplesheet are checked against JSON Schemas
before a job is planned.

## Repository layout

| Path | Contents |
| --- | --- |
| `workflow/` | Snakefile, rules, envs, schemas, scripts, report captions |
| `config/` | config, samplesheet and evaluation intervals for the full run |
| `profiles/` | `local`, `slurm` and `test` Snakemake profiles |
| `tools/` | data fetch, test-data builder, accuracy regression check, macOS benchmark wrapper |
| `tests/` | pytest unit tests for the scripts and workflow-level tests |
| `.tests/` | bundled test data and the integration config |
| `docs/` | SOP, validation, testing, data sources, caller evaluation, capacity, walk-through, operations |

## Documentation

* `docs/sop.md`: operating procedure for one run.
* `docs/validation.md`: accuracy against GIAB with commands and limits.
* `docs/testing.md`: test layers and how to run each.
* `docs/evaluation/caller_evaluation.md`: which caller to deploy and why.
* `docs/capacity_planning.md`: measured costs and a labelled projection to
  hundreds of genomes on Slurm.
* `docs/code_walkthrough.md`: a reviewer's tour of the code.
* `docs/data_sources.md`: every input with URL, size and SHA-256.
* `docs/operations/`: runbook and postmortems.
* `ROADMAP.md`, `CHANGELOG.md`, `CONTRIBUTING.md`.

## Licence and citation

Apache-2.0. Cite with `CITATION.cff`. The workflow uses public GIAB, GA4GH
stratification and ClinVar data; cite those resources as listed in
`docs/validation.md`.

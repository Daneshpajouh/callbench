# Standard operating procedure: germline benchmark run

Version 1.0.0, 2026-10-19. Owner: Amir Daneshpajouh.

This SOP covers one benchmark run: from a samplesheet of paired FASTQ files
with GIAB truth sets to an HTML report with accuracy, runtime and memory per
caller. It assumes a Unix shell, Python 3.12 or later and conda 24.7.1 or
later on `PATH`.

## 1. Prepare the software

1. Clone the repository and check out a release tag, not a branch:
   `git checkout v1.0.0`.
2. Create the Python environment that runs Snakemake:
   `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
3. Confirm the versions: `.venv/bin/snakemake --version` prints `9.27.0`;
   `conda --version` prints 24.7.1 or later.
4. On macOS only, run Snakemake through `tools/snakemake_macos.py` (the
   Makefile does this). Without it the benchmark files hold `NA` for memory
   and CPU; see `docs/operations/postmortems/2026-10-19-benchmark-na-on-macos.md`.

## 2. Prepare the inputs

1. On a host with internet access (a login or transfer node on a cluster),
   run `tools/fetch_public_data.sh <data dir>`. It writes `MANIFEST.tsv` in
   the data directory.
2. Compare `MANIFEST.tsv` with the SHA-256 values in `docs/data_sources.md`.
   A mismatch on reads or truth files means the source changed: stop and
   record it before running anything.
3. Link the data directory to `resources/full`
   (`ln -s <data dir> resources/full`) or edit the paths in
   `config/config.yaml`.
4. Edit `config/samples.tsv`: one row per sample with `sample`, `fq1`, `fq2`
   and, for benchmarked samples, `truth_vcf` and `truth_bed`. Sample ids are
   letters and digits only; the schema rejects anything else.
5. Edit `config/regions.bed` if the evaluation intervals change. Keep them at
   least 50 kb inside the fetched read windows.

## 3. Check before running

1. `make lint`: all five linters pass.
2. Dry run: `.venv/bin/snakemake --profile profiles/local -n`. Read the job
   table; for one sample and two callers on the default config it lists 36
   jobs before the scatter checkpoint expands.
3. Build the software environments ahead of the run so a solver failure does
   not stop a run halfway:
   `.venv/bin/snakemake --profile profiles/local --conda-create-envs-only`.
   This does not cover rules downstream of the scatter checkpoint (the
   calling rules), because they are not in the DAG until the checkpoint has
   run. Create those with a dry run of the calling rules after the first
   checkpoint, or run the test profile once, which builds every environment.

## 4. Run

Workstation (8 cores, 24 GB budget, low priority):

```
make run
```

Slurm cluster: set `slurm_account` and `slurm_partition` in
`profiles/slurm/config.v8+.yaml`, then from a login node:

```
.venv/bin/snakemake --profile profiles/slurm
```

Do not start heavy runs between 22:00 and 06:00 Pacific on shared
workstations. Every rule writes its log to `logs/<rule>/<wildcards>.log` and
its resource usage to `benchmarks/<rule>/<wildcards>.tsv`.

## 5. Check the outputs

1. `results/qc/qc_summary.tsv`: mean depth over the evaluation intervals
   between 25x and 40x for the bundled data, duplicate and error rates as in
   `docs/validation.md`. A large change means the input changed.
2. `results/report/accuracy.tsv`: compare the `all` rows with the release
   values in `docs/validation.md`. A drop of more than 0.005 in F1 for any
   caller and type is a regression; open a bug report before using the calls.
3. `results/report/profiling.by_rule.tsv`: peak memory per rule should stay
   under the `mem_mb` the rule requested. If it does not, raise the
   coefficients in `workflow/rules/common.smk`.

## 6. Report and archive

1. `make report` writes `results/report.html`, a self-contained file with
   the tables, figures, rule code and software versions.
2. Archive the report, `config/`, the `MANIFEST.tsv` of the inputs and the
   git commit hash together. These four items are enough to rerun the
   analysis.

## 7. When something fails

Follow `docs/operations/runbook.md`. Record anything that cost more than an
hour, or that produced wrong output, as a postmortem in
`docs/operations/postmortems/` using the template there.

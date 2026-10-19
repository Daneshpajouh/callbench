# Runbook

What to do when a run fails or its output looks wrong. Each entry below is a
failure that happened while building v1.0.0 on 2026-10-19, with the symptom
as it appeared, the cause and the fix. Times are Pacific.

## First steps for any failure

1. Find the failed rule: `grep -n "Error in rule" <snakemake log>`. Snakemake
   prints the rule, wildcards, shell command and the path of the rule log.
2. Read the rule log under `logs/<rule>/`. Every rule redirects stderr there.
3. Re-run only that job with its output as the target, for example
   `.venv/bin/snakemake --profile profiles/local results/calls/HG002/freebayes.raw.vcf.gz`.
4. If the job was killed for memory or time on Slurm, it is retried with
   1.5 times the memory and twice the runtime (see `mem_mb` and `runtime_min`
   in `workflow/rules/common.smk`; the slurm profile allows two retries).
   `sacct -j <jobid> --format=JobID,State,MaxRSS,Elapsed,ReqMem` shows what it
   used before it was killed.
5. Resume the run with the same command. `rerun-incomplete` is on in every
   profile, so half-written outputs are removed and rebuilt.

## Known failure modes

### Benchmark files hold NA for memory and CPU (macOS)

Symptom: `Benchmark: unable to collect cpu and memory benchmark statistics:`
with an empty message; `benchmarks/*/*.tsv` has `NA` after the wall time.
Cause: psutil has no `Process.io_counters` on macOS and Snakemake 9.27 drops
the whole sample on the resulting `AttributeError`.
Fix: run Snakemake through `tools/snakemake_macos.py` (the Makefile does).
Postmortem: `postmortems/2026-10-19-benchmark-na-on-macos.md`.

### A conda environment cannot be solved halfway through a run

Symptom (11:44, attempt 2): the run stopped after 158 s with
`LibMambaUnsatisfiableError ... freebayes-1.3.10 requires htslib >=1.21,<1.22.0a0`.
Cause: `workflow/envs/freebayes.yaml` pinned `bcftools=1.23.1`, which needs
htslib 1.23. FreeBayes 1.3.10 on bioconda is built against htslib 1.21.
`--conda-create-envs-only` had passed earlier because the calling rules sit
behind the scatter checkpoint and are not in the DAG until it runs.
Fix: pin `bcftools=1.21` next to FreeBayes. Before a production run, build
all environments with a run of the test profile, which reaches every rule.

### temp() index files deleted before the gather step

Symptom (11:47, attempt 3): `gather_calls` failed with
`Could not retrieve index file for 'results/calls/HG002/freebayes/chunks/0001.vcf.gz'`.
Cause: the per-chunk `.tbi` files were `temp()` outputs of the calling rules,
but `gather_calls` only declared the `.vcf.gz` files as input. Snakemake
deletes a temp file once no pending job lists it as input, so each index was
removed seconds after it was written.
Fix: `gathered_chunks()` in `common.smk` returns both the VCFs and their
indexes, and `gather_calls` declares both as named inputs.

### Python script fails with "from __future__ imports must occur at the beginning of the file"

Symptom (11:38, attempt 1): every `script:` rule failed with a SyntaxError
pointing at line 10 of a temporary copy under `.snakemake/scripts/`.
Cause: Snakemake's `script` directive inserts its preamble after the module
docstring; a `from __future__` import that follows the docstring is then no
longer first.
Fix: the scripts do not use `from __future__` (they need Python 3.12 anyway,
which has the `X | None` syntax natively).

### FASTQ files named .fastq.gz are not gzip

Symptom (11:19, data fetch): `gzip: HG002_R1.fastq.gz: not in gzip format`;
R1 and R2 had byte-identical sizes.
Cause: `samtools fastq` chooses compression from the output file name, and the
fetch script wrote to `<name>.fastq.gz.tmp` before renaming.
Fix: temporary names end in `.partial.fastq.gz`, and the script runs
`gzip -t` before the rename.

## Checks after a fix

* `make lint test` passes.
* `make test-workflow` passes and `tools/check_accuracy.py` reports no
  regression against `.tests/expected_accuracy.tsv`.
* For a fix that touches calling or evaluation, rerun the full-size data and
  compare `results/report/accuracy.tsv` with `docs/validation.md`.

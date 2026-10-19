# Logging

What a run records before, during and after it executes. Paths are relative
to the working directory of the run.

## Before: run manifest

The `onstart` handler in `workflow/Snakefile` calls
`workflow/scripts/runlog.py` before the first job and writes
`results/run/manifest.json`: start time (UTC), host, platform, Python and
Snakemake versions, git commit and whether the tree had uncommitted changes,
the command line, the full config, the pinned packages of every conda
environment, and every input file named by the config or samplesheet with its
size and SHA-256. A missing input is listed with `"missing": true`.

Excerpt from the test run of 2026-10-19 12:11 Pacific:

```
"start_utc": "2026-10-19T19:11:42+00:00",
"host": "Mac-Studio.local",
"snakemake": "9.27.0",
"git": {"commit": "a1509be0f82e0d20dc6e303b3d428f61d50a6fe3", "dirty": true},
"command": ["tools/snakemake_macos.py", "--profile", "profiles/test", "--forceall"],
```

## During: rule logs and benchmarks

Every rule writes stderr to `logs/<rule>/<wildcards>.log`. The Python scripts
log through one setup (`workflow/scripts/logsetup.py`): timestamp, level,
rule and sample on each line, level from `log_level` in the config. Errors on
bad input name the file and line before the job fails. From the same run:

```
2026-10-19 12:11:49,406 INFO rule=scatter_intervals sample=- read 1 intervals from results/ref/regions.bed
2026-10-19 12:11:49,418 INFO rule=scatter_intervals sample=- wrote 4 chunks of at most 50000 bp to results/scatter
2026-10-19 12:12:10,858 INFO rule=stratified_metrics sample=HG002 reading vcfeval tp-baseline, fn, tp and fp for bcftools and 6 strata
```

Every heavy rule also has a `benchmark` file under `benchmarks/<rule>/`, with
wall time, peak RSS, CPU time and mean load for that job. Snakemake's own log
(`.snakemake/log/<timestamp>.snakemake.log`) has a timestamped line for each
job that starts and finishes, with its rule and wildcards.

## After: run summary

The `onsuccess` and `onerror` handlers write `results/run/summary.json`:
status (`success` or `error`), start and end time, wall time, the per-rule
table built from the benchmark files, every final output with size and
SHA-256 (or `"missing": true`), and the path of every rule log. From the same
run: `"status": "success"`, 8 outputs, 43 rule logs.

`make report` adds the self-contained HTML report with the same tables,
figures, the rule code and software versions.

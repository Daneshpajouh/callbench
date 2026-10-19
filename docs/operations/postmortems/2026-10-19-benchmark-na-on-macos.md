# Postmortem: benchmark files recorded NA for memory and CPU on macOS

Date of incident: 2026-10-19. Author: Amir Daneshpajouh. Status: mitigated in
this repository; upstream fix not yet proposed.

## Summary

The first full-size run on the development Mac (Apple Silicon, macOS 27,
Snakemake 9.27.0, psutil 7.2.2) wrote benchmark files with wall time only.
`max_rss`, `max_vms`, `max_uss`, `mean_load` and `cpu_time` were `NA` for
every job, and the log showed
`Benchmark: unable to collect cpu and memory benchmark statistics:` with an
empty message. The peak-memory column of the profiling table, which the
resource functions and the capacity projection depend on, would have been
empty.

## Impact

No wrong numbers were published: the problem was seen on the first job
(fastp) about 30 seconds into the run, and the run was stopped and restarted.
Cost: one restart and about 20 minutes of investigation. Runs on Linux,
including any Slurm run, are not affected.

## Timeline (Pacific time, 2026-10-19)

* 11:38:08 First full run started (`snakemake --profile profiles/local`).
* 11:38:39 fastp finished; the log printed the benchmark warning.
* 11:40 `benchmarks/fastp/HG002.tsv` read: `24.91  0:00:24  NA  NA ...`.
* 11:41 Cause found by reading `snakemake/benchmark.py` and testing psutil.
* 11:41:05 Run restarted through `tools/snakemake_macos.py`.
* 11:42 `benchmarks/fastp/HG002.tsv` now had `max_rss` and `cpu_time`.

## Detection

A person reading the first benchmark file. Nothing in the workflow checked
that benchmark files had numbers in them.

## Root cause

Snakemake samples each job's process tree with psutil. In
`BenchmarkTimer._update_record` it calls `proc.io_counters()` and handles
`NotImplementedError` by switching I/O sampling off. On macOS psutil does not
define `Process.io_counters` at all, so the call raises `AttributeError`
instead:

```
$ .venv/bin/python -c "import psutil; p = psutil.Process(); print(hasattr(p, 'io_counters'))"
False
```

The caller, `BenchmarkTimer.work`, catches `AttributeError` as "process died
in flight" and discards the whole sample. Every sample of every job is
discarded, so nothing is collected and the record is written as `NA`.

## Fix

`tools/snakemake_macos.py` adds `Process.io_counters` to psutil when it is
missing, raising `NotImplementedError`, then calls Snakemake's normal entry
point. Snakemake then takes its existing path: it stops asking for I/O and
records memory and CPU. The Makefile runs Snakemake through this wrapper; on
Linux the wrapper changes nothing because psutil already has the method.

## Verification

After the restart, `benchmarks/fastp/HG002.tsv` read
`25.13  0:00:25  1195.78  ...  94.62  24.64` (wall seconds, max RSS in MB,
mean load, CPU seconds), and every later benchmark file had numbers. The
`io_in` and `io_out` columns stay empty on macOS, which is expected.

## What went well

* The benchmark directive was on every heavy rule from the start, so the gap
  showed up on the first job, not after the report was built.

## What went badly

* The warning message was empty, which hid the cause.
* Nothing checked the benchmark files; the run would have finished "green".

## Action items

| Action | Owner | Due | State |
| --- | --- | --- | --- |
| Wrapper `tools/snakemake_macos.py`, used by the Makefile | Amir Daneshpajouh | 2026-10-19 | done |
| `profiling_table` rule to fail when every `max_rss` value is NA | Amir Daneshpajouh | v1.1.0 | open (ROADMAP M1) |
| Report the AttributeError handling to the Snakemake project with this reproduction | Amir Daneshpajouh | v1.1.0 | open, not yet filed |

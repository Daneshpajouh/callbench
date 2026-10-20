# Code walk-through

A guided tour for a reviewer, in the order the data flows. Allow 20 minutes.
File paths are relative to the repository root.

## 1. Entry point and configuration

`workflow/Snakefile` pins the minimum Snakemake version, loads
`config/config.yaml`, names the report template and includes one rule file per
stage; the order of the includes is the order of the pipeline. Its `onstart`
and `onsuccess`/`onerror` hooks write the run manifest and run summary
(`workflow/scripts/runlog.py`).

`workflow/rules/common.smk` runs first. Read it before any rule file:

* `validate(config, ...)` and `validate(samples, ...)` check the config and
  the samplesheet against the JSON Schemas in `workflow/schemas/` before any
  job is planned. A misspelled caller name or a sample id with a hyphen fails
  here, not three hours into a run.
* `wildcard_constraints` limit `{sample}`, `{caller}` and `{stratum}` to the
  values in the config and `{chunk}` to four or more digits. Without them a
  pattern such as `results/calls/{sample}/{caller}.raw.vcf.gz` could match a
  sample called `HG002/bcftools`.
* Input functions (`get_fastqs`, `get_truth`, `read_group`) turn wildcards
  into paths from the samplesheet, so adding a sample is a one-line change to
  `config/samples.tsv`.
* `mem_mb()` and `runtime_min()` return functions of `input.size_mb` and
  `attempt`. A job's memory request grows with its input and by 1.5 times on
  each retry; on Slurm that turns an out-of-memory kill into a resubmission
  with more memory instead of a failed run.

## 2. Reference and QC (`ref.smk`, `qc.smk`)

The reference is symlinked into `results/ref/` so its indexes (bwa, faidx,
RTG SDF, minimap2) are written next to it under `results/`, never into the
shared data folder. `fastp` trims; `samtools stats` and `mosdepth` run on the
duplicate-marked BAM restricted to the evaluation intervals; `qc_summary`
joins them into one row per sample.

## 3. Alignment (`align.smk`)

`bwa_mem` and `minimap2_align` both stream into `samtools fixmate -m` and
`samtools sort`, so no unsorted BAM is written. `config["aligner"]` selects
which one `markdup` reads; the other is never scheduled. `bwa mem -K
100000000` fixes the batch size so output does not depend on the thread
count, which keeps the regression test deterministic.

## 4. Scatter, call, gather (`call.smk`)

`scatter_intervals` is a checkpoint. It splits the evaluation intervals into
chunks of at most `scatter.chunk_size` bp (500 kb for the full run, 50 kb for
the test), and the number of calling jobs is only known after it runs.
`scatter_chunks()` in `common.smk` calls `checkpoints.scatter_intervals.get()`
to read the chunk list back, and `gathered_chunks()` builds the per-chunk VCF
and index paths from it.

Each caller is an adapter rule with one output contract: a bgzipped, indexed,
single-sample VCF per chunk at `results/calls/{sample}/{caller}/chunks/`.
Everything after `gather_calls` is caller-agnostic. Adding a caller touches
five files (the adapter rule, an env file, the schema enum, the config and the
expected accuracy table); see `docs/evaluation/caller_evaluation.md`.

`gather_calls` uses `bcftools concat --allow-overlaps --remove-duplicates`
because a deletion that starts near a chunk boundary can be reported by both
neighbours. It lists the chunk `.tbi` files as inputs; leaving them out was a
real bug (see `docs/operations/runbook.md`).

`normalise` applies the same treatment to every caller: keep non-reference
genotypes passing the per-caller filter, left-align and split multi-allelic
records against the reference, split FreeBayes complex alleles with
`--atomize`, drop exact duplicates.

## 5. Evaluation (`evaluate.smk`)

`confident_regions` intersects the GIAB confident BED with the evaluation
intervals (pure Python in `workflow/scripts/intersect_bed.py`, unit tested).
`vcfeval` compares calls with truth inside those regions using
`--evaluation-regions`, which allows haplotype matches that cross a region
boundary. `stratified_metrics` counts the four vcfeval output VCFs by variant
type inside each GIAB stratum and computes precision, recall and F1 with the
GA4GH definitions (truth-side counts for recall, call-side counts for
precision).

## 6. Annotation and report (`annotate.smk`, `report.smk`)

ClinVar uses contig names without `chr`. `clinvar_subset` restricts ClinVar
to the evaluation intervals first and renames contigs second, so the rename
touches about 16,000 records rather than 3 million. `annotate_clinvar`
matches on CHROM, POS, REF and ALT (`--pair-logic exact`).

`profiling_table` reads every file the `benchmark` directive wrote and
produces per-job and per-rule tables. All report outputs are wrapped in
`report()` with an RST caption in `workflow/report/`, so `snakemake --report`
builds one HTML file with tables, figures, code and software versions.

## 7. Tests

`tests/` holds pytest unit tests for every script; `.tests/integration/` is
the end-to-end run on a 200 kb slice; `tools/check_accuracy.py` turns that run
into a regression test against `.tests/expected_accuracy.tsv`. The layers and
how to run each are in `docs/testing.md`.

## Things to question in review

* The evaluation intervals are 3.8 Mb around two genes. Results here say how
  the callers behave in these windows, not genome-wide; `docs/validation.md`
  states the selection bias.
* Peak memory comes from Snakemake's sampler, which takes its first sample
  quickly and then every 30 s. Jobs shorter than a few seconds show the shell
  wrapper's memory (about 9 MB), not the tool's.

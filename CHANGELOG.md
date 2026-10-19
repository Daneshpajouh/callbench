# Changelog

All notable changes to this workflow. Versions follow semantic versioning as
defined in `CONTRIBUTING.md`: a change to the output contract or the config
schema is MAJOR, a new caller, rule or report section is MINOR, a fix is PATCH.

## [Unreleased]

## [1.0.1] - 2026-10-19

### Fixed

* `docs/data_sources.md` no longer names a path on the build machine.

### Documented

* Cause of the one-record FreeBayes indel difference between runs: FreeBayes
  gave one homopolymer deletion QUAL 4.9e-06 in one run and 47.8 in another
  on the same BAM.

### Changed

* bcftools 1.23.1 to 1.24 in `workflow/envs/bcftools.yaml`; accuracy identical
  on HG002, runtime within 0.1 s per caller. Record:
  `docs/changes/2026-10-19-bcftools-1.24.md`.

## [1.0.0] - 2026-10-19

### Added

* Snakemake 9 workflow: fastp, bwa mem (minimap2 -ax sr as an alternative),
  samtools markdup, samtools stats, mosdepth.
* Calling with bcftools 1.23.1 and FreeBayes 1.3.10, scattered over a
  checkpoint-generated chunk list and gathered per sample and caller.
* Normalisation with bcftools norm (split, left-align, atomise FreeBayes
  complex alleles) and a per-caller quality filter.
* Benchmarking against GIAB v4.2.1 with RTG vcfeval 3.13, stratified by five
  GIAB v3.3 strata, by SNV and indel.
* ClinVar annotation (release 2026-10-11) with exact allele matching.
* Profiling table built from the benchmark directive of every heavy rule.
* `snakemake --report` output with RST captions for every table and figure.
* JSON Schema validation of the config and samplesheet.
* Profiles for a workstation, Slurm (snakemake-executor-plugin-slurm) and the
  bundled test data.
* `tools/fetch_public_data.sh` (region and index fetches from the GIAB mirror
  on AWS Open Data, with a SHA-256 manifest) and `tools/make_test_data.sh`.
* `tools/snakemake_macos.py` so the benchmark directive records memory and CPU
  on macOS.
* Run manifest (onstart) and run summary (onsuccess, onerror) under
  `results/run/`, and one logging setup for the Python scripts with rule and
  sample on each line.
* Dockerfile from `snakemake --containerize`, base image pinned by digest,
  and a release job that publishes it to ghcr.io.
* 349 unit tests on hand-written fixtures, dry-run and lint tests, an
  end-to-end test on a 200 kb HG002 slice and an accuracy regression check.
* Documentation: SOP, validation report, testing, logging, data sources,
  caller evaluation memo, capacity projection, code walk-through, runbook,
  one postmortem.

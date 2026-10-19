# Changelog

All notable changes to this workflow. Versions follow semantic versioning as
defined in `CONTRIBUTING.md`: a change to the output contract or the config
schema is MAJOR, a new caller, rule or report section is MINOR, a fix is PATCH.

## [Unreleased]

Planned as 1.0.2. Calls change for FreeBayes (padding), so the full-size and
test-profile results need a rerun before release; the figures in
`docs/validation.md` are those of 1.0.1 until then.

### Added

* Opt-in comparison across the QUAL score (`evaluation.roc`): vcfeval on
  unfiltered calls with `--vcf-score-field QUAL`, summarised in
  `results/report/roc_summary.tsv` as best F1 and recall at a target precision.

### Changed

* FreeBayes calls each chunk padded by `scatter.call_padding` (default 1000 bp)
  and keeps only records whose POS lies in the unpadded chunk, so a variant
  near a chunk edge is called with its full haplotype window.
* `tools/check_accuracy.py` also requires the truth count (tp_base + fn) to
  match, and fails a stratum with no expected F1 when false positives appear.
* CI job `lint` renamed `checks`; it also runs the tests.

### Documented

* Caller memo: the default rests on SNV accuracy and cost, with exact tests;
  the easy-indel gap (2 against 9 of 196, p about 0.06) is marked suggestive.
* One measured test-data size (5.5 MB), the five files a new caller touches,
  the read count before fastp, and a coverage excerpt from the current tree.

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

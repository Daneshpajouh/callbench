# Test fixtures

Small hand-written inputs for the unit tests in `tests/unit`. Each file is a few
lines so a failing test can be read against its input. `test_fixtures.py` checks
that each file still has the property named below. The gzip files use a fixed
modification time so their bytes do not change between rebuilds.

| Fixture | What it exercises | Used by |
|---|---|---|
| `reads_R1.fastq.gz`, `reads_R2.fastq.gz` | Paired FASTQ, 5 records each, gzip. Read names end in `/1` and `/2`, sequences are 26 to 30 bases, qualities match the sequence length. | `test_fixtures.py` (pairing, and the read and base counts in `fastp.json`) |
| `header_only.vcf` | VCF with a full header and no records. | `test_stratified_metrics.py` (`count_records` returns 0; empty `fp` input to the rule script), `test_fixtures.py` |
| `multiallelic.vcf` | Four records, one with two ALT alleles (`A` to `G,AT`). `bcftools view -v` counts that record under both `snps` and `indels`. | `test_stratified_metrics.py` (type counts, region filtering, rule script), `test_fixtures.py` |
| `malformed_columns.vcf` | A data line with 7 columns where the header has 10. bcftools rejects the file. | `test_stratified_metrics.py` (error names the file), `test_fixtures.py` |
| `missing_info.vcf` | Records whose INFO field is `.` beside one with `DP=3`. | `test_stratified_metrics.py`, `test_fixtures.py` |
| `with_chr_prefix.bed` | Three intervals on `chr17` and `chr13`. | `test_scatter_intervals.py`, `test_intersect_bed.py` (contig-name mismatch against `without_chr_prefix.bed`), `test_fixtures.py` |
| `without_chr_prefix.bed` | The same intervals on `17` and `13`. Intersecting with the prefixed BED gives nothing. | `test_intersect_bed.py`, `test_fixtures.py` |
| `empty.bed` | Zero-byte BED, the shape of a stratum that misses the evaluation regions. | `test_scatter_intervals.py`, `test_intersect_bed.py`, `test_fixtures.py` |
| `crlf.bed` | BED with Windows line endings, a `#` header line, a blank line and a name column. `.gitattributes` keeps git from converting it. | `test_scatter_intervals.py`, `test_intersect_bed.py`, `test_fixtures.py` |
| `regions.bed.gz`, `regions.bed` | The same three intervals gzipped and plain, for the gzip and plain readers. | `test_intersect_bed.py`, `test_scatter_intervals.py` (plain only), `test_fixtures.py` |
| `fastp.json` | fastp report trimmed to the fields the QC table reads: 10 reads before filtering, 8 after, duplication rate 0.0521. | `test_qc_summary.py`, `test_fixtures.py` |
| `samtools_stats.txt` | Excerpt of `samtools stats` with comment lines, `SN` lines with trailing comments, and non-`SN` sections. | `test_qc_summary.py`, `test_fixtures.py` |
| `mosdepth_with_total_region.summary.txt` | mosdepth summary from a run with `--by`: per-contig rows, `total`, per-region rows and `total_region` (mean 32.5). | `test_qc_summary.py`, `test_fixtures.py` |
| `mosdepth_without_total_region.summary.txt` | The same without `--by`, so only `total` exists (mean 0.02). | `test_qc_summary.py`, `test_fixtures.py` |
| `benchmark_with_na.tsv` | Snakemake benchmark file as written on macOS without the psutil shim: wall time present, every resource column `NA`. | `test_profiling_table.py`, `test_fixtures.py` |
| `clinvar_zero_rows.tsv` | ClinVar table from `clinvar_table` with the header and no rows. | `test_clinvar_summary.py`, `test_fixtures.py` |
| `accuracy_expected.tsv` | Expected accuracy table: two scored rows and one stratum with NA metrics. | `test_check_accuracy.py`, `test_logsetup.py`, `test_fixtures.py` |
| `accuracy_observed_with_na.tsv` | Observed table for the same keys: SNV F1 dropped to 0.89 and the INDEL row is NA. | `test_check_accuracy.py`, `test_aggregate_tables.py`, `test_plots.py`, `test_fixtures.py` |

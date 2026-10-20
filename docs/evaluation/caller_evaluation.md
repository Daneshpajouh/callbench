# Caller evaluation: which germline small-variant caller to deploy

Internal technical memo. Author: Amir Daneshpajouh. Date: 2026-10-19.
Status: recommendation, numbers from the v1.0.2 run; revisit at milestone M3
(GATK and DeepVariant adapters).

## Decision asked for

Which caller should be the default in this pipeline, and how should a new
caller be added to an existing production pipeline without disturbing it.

## Criteria, in priority order

1. Accuracy on GIAB HG002 v4.2.1 by variant type and stratum, with indel F1
   weighted as heavily as SNV F1, because clinically relevant variants in
   BRCA1 and BRCA2 include many small indels.
2. Failure behaviour: does the caller fail loudly, and can a failed chunk be
   retried on its own.
3. Runtime and peak memory per genome, from the benchmark directive.
4. Licence that allows use in a public-sector clinical setting.
5. Maintenance: release cadence and whether the project is active.
6. Packaging: native builds for the hardware we run on, and containers
   pinned by digest.

## Candidates

Run and measured: bcftools 1.24 (`mpileup | call -m`; v1.0.0 used 1.23.1 with
identical accuracy) and FreeBayes 1.3.10. Not run: GATK HaplotypeCaller and
DeepVariant.
Both ship as linux/amd64 containers only; on the Apple Silicon build host they
would run under emulation and their runtimes would not represent a Linux
cluster. They are milestone M3 in `ROADMAP.md`, to be measured on native
amd64. No accuracy number in this memo comes from either of them.

## 1. Accuracy (HG002, 3.8 Mb, about 29x)

From `docs/results-v1.0.2/accuracy.tsv` (full table in `docs/validation.md`):

| Caller | SNV F1 | Indel F1 | Indel recall | Indel precision | SNV FP | Indel FP |
| --- | --- | --- | --- | --- | --- | --- |
| bcftools | 0.9972 | 0.9185 | 0.9117 | 0.9254 | 7 | 50 |
| FreeBayes | 0.9952 | 0.9318 | 0.9087 | 0.9560 | 17 | 28 |

By stratum, the difference is concentrated in two places:

* Outside difficult regions (2,995 SNVs, 196 indels) bcftools is better on
  both: SNV F1 0.9995 against 0.9978 and indel F1 0.9898 against 0.9663.
  FreeBayes misses 9 of those 196 easy indels; bcftools misses 2.
* In low-complexity sequence (440 indels) FreeBayes is better: indel F1 0.9153
  against 0.8855, from 23 false positives against 47.

The strata with segmental duplications and low mappability hold 5 or 6
indels; the callers tie there and the counts are too small to separate them.

## 2. Failure behaviour

Observed while building v1.0.0 (details in `docs/operations/runbook.md`):

* Both callers run per 500 kb chunk, so a failed chunk is retried alone;
  neither needed a retry on this data.
* FreeBayes 1.3.10 on bioconda is built against htslib 1.21 and cannot share
  an environment with bcftools 1.23.1. The solver failure appeared only when
  the run reached the calling rules. bcftools has no such constraint.
* FreeBayes 1.3.10 is not fully deterministic: on the same BAM and chunk,
  one homopolymer deletion (chr17:43,430,368) got QUAL 4.9e-06 in one run
  and 47.8 in another, so it crossed the `QUAL>=20` filter one way or the
  other. bcftools gave identical output in every run.
* FreeBayes writes complex alleles (MNPs, combined SNV and indel blocks) that
  must be split with `bcftools norm --atomize` before comparison; without it
  the same variant can be scored as both a false positive and a false
  negative. bcftools output needs only the standard split and left-align.

## 3. Runtime and memory

From `docs/results-v1.0.2/profiling.by_rule.tsv`, the v1.0.2 run on 2026-10-19
(`--forceall`, 8 cores, Apple Silicon, native arm64 builds), eight 500 kb
chunks per caller:

| Caller | Wall time summed over chunks | Longest chunk | Peak RSS (largest chunk) |
| --- | --- | --- | --- |
| bcftools | 16.8 s | 2.5 s | 191 MB |
| FreeBayes | 18.6 s | 2.6 s | 371 MB |

FreeBayes took 1.11 times the wall time and 1.94 times the memory of
bcftools on the same chunks. The memory ratio is stable across runs (363 MB
against 185 MB in the earlier clean run measured in `docs/capacity_planning.md`);
the wall-time ratio is not (1.36 there).
Both are small next to alignment (bwa mem 16.2 s on 8 threads for 814,284
reads) and next to the one-off bwa index of the reference (146.6 s). CPU time from the benchmark directive is undercounted
for jobs this short, because Snakemake samples the process tree at intervals;
wall time is the reliable column here. In an earlier, interrupted run the
same FreeBayes chunks summed to 47.2 s, so expect run-to-run variation of
that order on a shared workstation.

## 4. Licence

| Caller | Licence (checked at source, 2026-10-19) |
| --- | --- |
| bcftools | MIT/Expat or GPL, at the user's choice; GPL applies if built with the optional GNU Scientific Library (LICENSE file in samtools/bcftools) |
| FreeBayes | MIT (GitHub repository metadata) |
| RTG Tools (evaluation only) | BSD-2-Clause |
| GATK (M3) | Apache-2.0 (LICENSE.TXT in broadinstitute/gatk) |
| DeepVariant (M3) | BSD-3-Clause |

All allow use and redistribution in this setting.

## 5. Maintenance (GitHub releases, read 2026-10-19)

| Project | Last three releases |
| --- | --- |
| bcftools | 1.24 (2026-07-09), 1.23.2 (2026-07-10), 1.22.2 (2026-07-10) |
| FreeBayes | v1.3.10 (2025-05-31), v1.3.9 (2025-02-16), v1.3.8-pre3 (2024-04-28) |
| RTG Tools | 3.13 (2025-05-28), 3.12.1 (2021-05-20), 3.12 (2021-01-27) |
| GATK | 4.7.0.0 (2026-08-18), 4.6.2.0 (2025-04-14), 4.6.1.0 (2024-10-30) |
| DeepVariant | v1.10.0 (2026-03-05), v1.10.0-beta (2025-10-09), v1.9.0 (2025-05-13) |

bcftools ships several releases a year and backports fixes to older minor
versions. FreeBayes has had no release for about 16 months.

## 6. Packaging

Both callers have native osx-arm64 and linux-64 builds on bioconda, which is
how they ran here. BioContainers images exist for both for apptainer on a
cluster. GATK and DeepVariant publish linux/amd64 images.

## Recommendation

Default caller: bcftools, on SNV accuracy and cost. Outside difficult
regions it makes 3 SNV errors against 13 in 2,995 (SNV F1 0.9995 against
0.9978; two-sided exact test on the 16 errors, p about 0.02), and it needs
about half the memory per chunk (191 MB against 371 MB peak). Its wall-time
lead (16.8 s against 18.6 s summed) is within run-to-run variation. It also
has the more active release history and no htslib pin conflict.

The indel difference outside difficult regions is suggestive only: bcftools
misses 2 of 196 easy indels and FreeBayes 9 (two-sided Fisher exact test,
p about 0.06). Both callers saw the same 196 indels in one sample, so the
right test is a paired one on the per-variant table; confirm it in M2.

Keep FreeBayes as a second caller in the benchmark, not as the default: its
indel precision in tandem repeats and homopolymers (23 false positives against
47; two-sided exact test on the 70 false positives, p about 0.006) is the one
place it is clearly better, and a later milestone can test a consensus or a
repeat-aware filter using that.

All three tests compare counts at the single `QUAL>=20` cut, one run, one
sample. Over all QUAL cuts ([validation](../validation.md), comparison
across the QUAL score) the ordering holds: best F1 0.9972 against 0.9952 for
SNVs in favour of bcftools, 0.9384 against 0.9201 for indels in favour of
FreeBayes. At precision 0.99 bcftools keeps more truth indels (46.8% against
35.9%), so FreeBayes's indel lead holds at the deployed cut and lower ones,
not at strict precision.

This recommendation holds for these two windows at about 29x. Confirm on the
four-sample cohort (M2) and against GATK and DeepVariant (M3) before using it
for a production decision.

## Adding a new caller to an existing pipeline

The pipeline is built so that a new caller touches five files (`call.smk`,
an environment file, the config schema, the config and the expected
accuracy table) and nothing downstream changes.

1. Adapter rule. Add `call_<name>` in `workflow/rules/call.smk` that reads
   the duplicate-marked BAM and one chunk BED and writes the output contract:
   `results/calls/{sample}/<name>/chunks/{chunk}.vcf.gz` plus `.tbi`,
   bgzipped, single sample named as the sample, `GT` present. Give it a
   `benchmark:` path, a `log:` path and resource functions from `common.smk`.
2. Environment. Add `workflow/envs/<name>.yaml` with exact versions, or a
   `container:` pinned by digest for apptainer.
3. Schema and config. Add the name to the `callers` enum in
   `workflow/schemas/config.schema.yaml` and a filter expression under
   `filters` in the config.
4. Regression tests. Run `make test-workflow`; add the new caller's rows to
   `.tests/expected_accuracy.tsv` from that run; `tools/check_accuracy.py`
   then guards both the new caller and the existing ones in CI.
5. Evidence for review. Open the "new caller" issue form and attach the
   full-size accuracy table, the per-rule profiling table and the licence.

Existing users see no change: the default `callers` list in their config
does not include the new caller until they add it, and every output path of
the existing callers is unchanged. That is a MINOR version bump.

# Validation report, v1.0.0

What was run, on what, with which command, and what came out. Every number
here comes from the files named next to it; nothing was typed in by hand.

## Run

* Date: 2026-10-19. Host: Mac Studio, Apple Silicon (arm64), 28 cores, 96 GB
  RAM, macOS 27. Snakemake 9.27.0 under `nice -n 10`, 8 cores, 24 GB budget.
* Software from the pinned conda environments in `workflow/envs/`, all
  native osx-arm64 builds from bioconda and conda-forge: fastp 1.4.0,
  bwa 0.7.19, samtools 1.23.1, mosdepth 0.3.14, bcftools 1.23.1 (1.21 in the
  FreeBayes environment), FreeBayes 1.3.10, RTG Tools 3.13. From v1.0.1 the bcftools
  environment pins 1.24; the rerun gave identical accuracy
  (`docs/changes/2026-10-19-bcftools-1.24.md`).
* Command:

  ```
  nice -n 10 .venv/bin/python tools/snakemake_macos.py --profile profiles/local --forceall
  ```

* Inputs: HG002 reads, GRCh38 chr13 and chr17, GIAB v4.2.1 truth, GIAB v3.3
  stratifications and ClinVar 2026-10-11, all listed with SHA-256 in
  `docs/data_sources.md`.
* Outputs read for this report: `results/report/accuracy.tsv`,
  `results/qc/qc_summary.tsv`, `results/report/profiling.by_rule.tsv`,
  `results/report/clinvar_summary.tsv`.

## Read and alignment QC (HG002)

From `results/qc/qc_summary.tsv`:

| Metric | Value |
| --- | --- |
| Read pairs x 2 before fastp | 850,492 |
| Reads after fastp | 814,284 |
| Q30 rate after fastp | 0.9144 |
| Reads mapped in evaluation intervals (samtools stats) | 771,476 |
| Properly paired | 769,885 |
| Marked duplicates | 3,432 |
| Mismatch rate | 0.0032 |
| Mean insert size | 544.1 bp |
| Mean depth over evaluation intervals (mosdepth) | 29.43x |

## Accuracy against GIAB v4.2.1

Evaluated inside the GIAB HG002 confident regions that overlap the evaluation
intervals. Comparison with RTG vcfeval (`--ref-overlap`,
`--evaluation-regions`), counts by variant type from the four vcfeval output
VCFs. Recall uses truth-side counts (`tp_base`, `fn`) and precision uses
call-side counts (`tp_call`, `fp`), as in the GA4GH benchmarking definitions
used by hap.py. Both callers had the same filter, `QUAL>=20`.

All confident regions:

| Caller | Type | TP (truth) | FN | TP (calls) | FP | Recall | Precision | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bcftools | SNV | 3,400 | 12 | 3,403 | 7 | 0.9965 | 0.9979 | 0.9972 |
| bcftools | INDEL | 599 | 58 | 620 | 50 | 0.9117 | 0.9254 | 0.9185 |
| FreeBayes | SNV | 3,396 | 16 | 3,423 | 17 | 0.9953 | 0.9951 | 0.9952 |
| FreeBayes | INDEL | 597 | 60 | 609 | 28 | 0.9087 | 0.9560 | 0.9318 |

By stratum (F1, with truth counts in brackets):

| Stratum | bcftools SNV | FreeBayes SNV | bcftools INDEL | FreeBayes INDEL |
| --- | --- | --- | --- | --- |
| not_difficult | 0.9995 (2,995) | 0.9978 (2,995) | 0.9898 (196) | 0.9663 (196) |
| all_difficult | 0.9807 (417) | 0.9769 (417) | 0.8885 (461) | 0.9170 (461) |
| low_complexity | 0.9787 (188) | 0.9765 (188) | 0.8855 (440) | 0.9153 (440) |
| segdups | 0.9358 (56) | 0.9358 (56) | 0.8451 (6) | 0.8451 (6) |
| low_mappability | 0.9355 (64) | 0.9355 (64) | 0.8000 (5) | 0.8000 (5) |

Reading the table:

* Outside difficult regions both callers are close to perfect for SNVs;
  bcftools makes 3 errors in 2,995 and FreeBayes 13.
* Most errors are indels in low-complexity sequence (tandem repeats and
  homopolymers): 440 of the 657 truth indels sit there, and that is where both
  callers lose most of their indel accuracy. FreeBayes is more precise there
  (23 false positives against 47 for bcftools).
* The segdups and low_mappability strata hold 56 and 64 SNVs and 5 or 6
  indels. Ratios from 5 indels move by 0.2 for each error; do not compare
  callers on them.

## Run-to-run reproducibility

Three complete runs on the same inputs gave identical QC, identical bcftools
counts in every stratum and identical FreeBayes SNV counts. FreeBayes indel
counts differed by one record in low-complexity sequence: 596 true positives
(F1 0.9302) in a run started at 11:51 Pacific, 597 (F1 0.9318) in the clean
run reported above and in the bcftools 1.24 run.

Cause, found at 12:43: FreeBayes 1.3.10 itself. Running it twice on the same
BAM and the same 500 kb chunk (chr17:43,050,000-43,550,000) gave identical
records except one, a deletion of one T from a 19 bp homopolymer at
chr17:43,430,368, whose QUAL was 4.9e-06 in one run and 47.8 in the other.
With the `QUAL>=20` filter that record is dropped or kept. The other seven
chunks were byte-identical between the two runs. The input BAM, fastp output
order (checked: two 4-thread fastp runs gave identical files) and chunk
boundaries are not involved. Treat F1 differences below about 0.002 between
FreeBayes runs as noise; bcftools showed no such variation.

## Limits of this validation

* Interval selection. The evaluation intervals are two 1.9 Mb windows chosen
  because they contain BRCA1 and BRCA2, not a random sample of the genome.
  Their mix of repeats, duplications and GC content differs from the genome
  average, so genome-wide accuracy would differ. GIAB's own reports use whole
  chromosomes or the whole genome; this run does not replace them.
* Reads come from a region fetch of reads that GIAB's novoalign run placed in
  the windows. Reads from elsewhere in the genome that bwa would have placed
  here are missing, which can hide false positives caused by mismapped
  paralogous reads. The 50 kb margin keeps reads near the evaluation edges
  aligned in context, but does not fix this. Aligning to chr13 and chr17 only
  (not the whole genome) has the same effect in the other direction.
* One sample. HG001, HG003 and HG004 are fetched (`docs/data_sources.md`) and
  are milestone M2 in `ROADMAP.md`.
* Sampled memory. Snakemake's benchmark directive samples the process tree;
  jobs shorter than a few seconds report only the shell wrapper (about 9 MB).

## References

All DOIs checked to resolve on 2026-10-19.

* Wagner J. et al. Benchmarking challenging small variants with linked and
  long reads. Cell Genomics 2022. doi:10.1016/j.xgen.2022.100128 (GIAB v4.2.1)
* Krusche P. et al. Best practices for benchmarking germline small-variant
  calls in human genomes. Nature Biotechnology 2019.
  doi:10.1038/s41587-019-0054-x
* Dwarshuis N. et al. The GIAB genomic stratifications resource for human
  reference genomes. Nature Communications 2024.
  doi:10.1038/s41467-024-53260-y
* Cleary J. G. et al. Comparing variant call files for performance
  benchmarking of next-generation sequencing variant calling pipelines.
  bioRxiv 2015. doi:10.1101/023754 (RTG vcfeval)
* Danecek P. et al. Twelve years of SAMtools and BCFtools. GigaScience 2021.
  doi:10.1093/gigascience/giab008
* Garrison E., Marth G. Haplotype-based variant detection from short-read
  sequencing. arXiv 2012. doi:10.48550/arXiv.1207.3907 (FreeBayes)
* Li H. Aligning sequence reads, clone sequences and assembly contigs with
  BWA-MEM. arXiv 2013. doi:10.48550/arXiv.1303.3997
* Li H. Minimap2: pairwise alignment for nucleotide sequences.
  Bioinformatics 2018. doi:10.1093/bioinformatics/bty191
* Chen S. et al. fastp: an ultra-fast all-in-one FASTQ preprocessor.
  Bioinformatics 2018. doi:10.1093/bioinformatics/bty560
* Pedersen B. S., Quinlan A. R. Mosdepth: quick coverage calculation for
  genomes and exomes. Bioinformatics 2018. doi:10.1093/bioinformatics/btx699
* Landrum M. J. et al. ClinVar: improving access to variant interpretations
  and supporting evidence. Nucleic Acids Research 2018.
  doi:10.1093/nar/gkx1153
* Molder F. et al. Sustainable data analysis with Snakemake. F1000Research
  2021. doi:10.12688/f1000research.29032.2

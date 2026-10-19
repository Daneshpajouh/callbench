# Data sources

All inputs are public. Nothing under `resources/full/` is committed; the
bundled test data in `.tests/integration/data/` (about 4 MB) is derived from the files
below by `tools/make_test_data.sh`.

## Where the files come from, and why that host

Genome in a Bottle (GIAB) publishes the same tree on two hosts: the NCBI FTP
site `ftp-trace.ncbi.nlm.nih.gov` and the AWS Registry of Open Data bucket
`giab.s3.amazonaws.com`. On 2026-10-19 the robots.txt of the NCBI host read
`User-agent: *` / `Disallow: /`, so no script in this repository reads from
it. The S3 bucket has no robots.txt (HTTP 404) and is listed on the AWS
Registry of Open Data for public use. GIAB reference material is produced by
NIST and released without use restrictions; cite the GIAB papers listed in
`docs/validation.md` when publishing results.

Everything is fetched by region or index where the file format allows it:

* Reads: `samtools view` with htslib range requests against the remote BAM
  index. The HG002 whole-genome BAM is 126,230,242,948 bytes; the region fetch
  transferred about 100 MB of FASTQ output for two 2 Mb windows.
* Reference: `samtools faidx` against the remote bgzipped FASTA with its
  `.fai` and `.gzi`, pulling only chr13 and chr17.
* Truth VCFs: `bcftools view -R` against the remote `.tbi`.
* BED files are small and were downloaded whole.

`tools/fetch_public_data.sh` does all of this and writes `MANIFEST.tsv` with
the size, SHA-256, UTC fetch time, source URL and method of every file. The
table below is that manifest for the copy used in `docs/validation.md`
(fetched 2026-10-19 between 11:20 and 11:26 Pacific, 18:20 to 18:26 UTC).

## Fetched windows

| Window | GRCh38 interval | Gene of interest |
| --- | --- | --- |
| BRCA2 window | chr13:32,000,001-34,000,000 | BRCA2 (chr13:32.31-32.40 Mb) |
| BRCA1 window | chr17:42,500,001-44,500,000 | BRCA1 (chr17:43.04-43.13 Mb) |

The evaluation intervals in `config/regions.bed` sit 50 kb inside each window
(chr13:32,050,000-33,950,000 and chr17:42,550,000-44,450,000, 0-based BED), so
reads at the edges of what is scored still have mates and neighbouring reads.

## Reads

Source BAMs (NHGRI Illumina HiSeq 2500, 2x148 bp, aligned with novoalign to
GRCh38 by GIAB). Each was subsampled by template with seed 42 to about 30x:
HG002, HG003 and HG004 from their 60x BAMs (fraction 0.5), HG001 from its 300x
BAM (fraction 0.1). Secondary and supplementary records were dropped
(`-F 0x900`); duplicates were kept so `samtools markdup` has real work to do.
Templates with one mate outside the windows were dropped (3,211 singletons for
HG002).

| File | Bytes | SHA-256 |
| --- | --- | --- |
| reads/HG002_R1.fastq.gz | 48,303,598 | 0f31595fbe7137b4535dc4a3050ad0fcd00408ad8e17e7e9f1f000954049e9d5 |
| reads/HG002_R2.fastq.gz | 52,335,990 | 9def919b47f41a65fd964cff8f2f0dfa9be14d430435cce984885b8762a7b4ea |
| reads/HG001_R1.fastq.gz | 45,081,010 | 93b4af94247d91c6aafaf9bce37c6848795a978bb4177d4ec9f2a98905ea3137 |
| reads/HG001_R2.fastq.gz | 48,930,393 | 96844f041c1d50306e17b2c7b726f47aaaafc4288ad9105bea6f671ea76c1689 |
| reads/HG003_R1.fastq.gz | 43,346,374 | b26c488f5f0b8afd8a905cbeb5525278db29078202689f733050ca6282fe43e4 |
| reads/HG003_R2.fastq.gz | 46,906,358 | b57e2294f9dc1964a83a869acd1aea05f82553132d44656ca49c045f7aa42f4e |
| reads/HG004_R1.fastq.gz | 48,180,898 | b3e84dea65ac1b48718ca5dcbcb9fe88ff94c336ed918770bb0f474b4c24f926 |
| reads/HG004_R2.fastq.gz | 52,474,161 | 59be886d6559c4fcd833d256953883ed81292d0dd96d61aa3326b3e921644a77 |

Source URLs (prefix `https://giab.s3.amazonaws.com/`):

* HG002: `data/AshkenazimTrio/HG002_NA24385_son/NIST_HiSeq_HG002_Homogeneity-10953946/NHGRI_Illumina300X_AJtrio_novoalign_bams/HG002.GRCh38.60x.1.bam`
* HG003: `data/AshkenazimTrio/HG003_NA24149_father/NIST_HiSeq_HG003_Homogeneity-12389378/NHGRI_Illumina300X_AJtrio_novoalign_bams/HG003.GRCh38.60x.1.bam`
* HG004: `data/AshkenazimTrio/HG004_NA24143_mother/NIST_HiSeq_HG004_Homogeneity-14572558/NHGRI_Illumina300X_AJtrio_novoalign_bams/HG004.GRCh38.60x.1.bam`
* HG001: `data/NA12878/NIST_NA12878_HG001_HiSeq_300x/NHGRI_Illumina300X_novoalign_bams/HG001.GRCh38_full_plus_hs38d1_analysis_set_minus_alts.300x.bam`

HG001, HG003 and HG004 are fetched and hashed but not yet run; the cohort run
is milestone M2 in `ROADMAP.md`.

## Reference

| File | Bytes | SHA-256 |
| --- | --- | --- |
| reference/GRCh38_chr13_chr17.fa | 200,444,953 | ddefcd570d0e76caa055f352a502f2aa9846c7d8d43bcbf5e8f984c82c91c3db |

Source: `release/references/GRCh38/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.gz`
(chr13 and chr17 only). This is the no-alt analysis set GIAB used for the
v4.2.1 benchmarks, so truth and reference coordinates agree.

## Truth sets (GIAB v4.2.1, GRCh38)

| File | Bytes | SHA-256 | Method |
| --- | --- | --- | --- |
| truth/HG002_v4.2.1_regions.vcf.gz | 174,652 | 446bf891aa2b0a9a31ce13c4dc9bdb9ffb9d56576c40cc0a5f5cba22c4294cf9 | region fetch |
| truth/HG002_v4.2.1_benchmark.bed | 11,494,021 | fba9a57c36ec88e5d14ea3e259c8866c7935f4998d3ec0fa2d6c3962da5b5575 | whole file |
| truth/HG001_v4.2.1_regions.vcf.gz | 153,718 | d2fa7acbb76c68f0348af75286b5663c8d9389226631e97ae4b0f2be0f261bea | region fetch |
| truth/HG001_v4.2.1_benchmark.bed | 15,479,939 | dc3485e60447a3e863c34dfc063c3710ea5ed5efae50855c5197ba62538263b9 | whole file |
| truth/HG003_v4.2.1_regions.vcf.gz | 201,917 | ecc76afb4f6035c2ecb7b64efa512f4b16217272e28838bf3d88f0a3556eccb3 | region fetch |
| truth/HG003_v4.2.1_benchmark.bed | 13,219,856 | 652afd3046705af3200f9c87c255fef11bb212dd76c75a19999c9b2df8a3180c | whole file |
| truth/HG004_v4.2.1_regions.vcf.gz | 171,968 | 2892df265b2be2cefe286a74ffefe33e06025971087866ad1513237482644d0b | region fetch |
| truth/HG004_v4.2.1_benchmark.bed | 13,081,043 | 88d1c926fdc8abd9c39b3e9fe2af3fc43dd67d284690a3dc6127b369d96bccad | whole file |

Sources: `release/AshkenazimTrio/HG00{2,3,4}_*/NISTv4.2.1/GRCh38/HG00x_GRCh38_1_22_v4.2.1_benchmark.vcf.gz`
and `..._benchmark_noinconsistent.bed`;
`release/NA12878_HG001/NISTv4.2.1/GRCh38/HG001_GRCh38_1_22_v4.2.1_benchmark.vcf.gz` and `.bed`.
The whole HG002 truth VCF is 156,252,944 bytes; the region fetch is 174,652.

## Stratifications (GIAB v3.3, GRCh38)

Each file's MD5 was checked against the published
`GRCh38-genome-stratifications-md5s.txt` before use.

| Stratum name in config | File | Bytes | SHA-256 |
| --- | --- | --- | --- |
| low_complexity | GRCh38_AllTandemRepeatsandHomopolymers_slop5.bed.gz | 30,355,634 | e367c4bcca801df9f8ad6529eda1859625fe125d30813730ba2112d530cdf7d2 |
| segdups | GRCh38_segdups.bed.gz | 65,091 | 413b505be7985d05746e6ab2a1332a3fda515b49688246ca7ace680c1744a032 |
| low_mappability | GRCh38_lowmappabilityall.bed.gz | 4,871,989 | 4b487e8500d756335489b41ae31fa594f3967655f29e3d804d3e159c04f294c9 |
| all_difficult | GRCh38_alldifficultregions.bed.gz | 31,491,634 | 65f302d7d484d1b5e413f4ebf20cdb7f68341e6c73581c1ee0e9c5446c0d2451 |
| not_difficult | GRCh38_notinalldifficultregions.bed.gz | 32,737,709 | 4b720f25555c4ae64dbab1578e53a64407f7e90b2ebee72eaaafce3bd9f92cbb |

Source prefix: `release/genome-stratifications/v3.3/GRCh38@all/` with
subfolders LowComplexity, SegmentalDuplications, Mappability and Union.

## ClinVar

| File | Bytes | SHA-256 |
| --- | --- | --- |
| clinvar.vcf.gz (release 2026-10-11) | 200,437,060 | 05d9481dd7217cc4df15803362d4a4c9eae5875b27b1750867d6bfd2643b3d10 |

This copy was fetched on 2026-10-19 by another of the author's projects into
the shared folder `/Volumes/MXFAST/data/portfolio/clinvar/` and is reused here
rather than downloaded again. Its MD5 (`0f3a1a5e84252386033d5fcab1bf1f6a`)
matches the `.md5` file NCBI publishes beside it, which names
`clinvar_20261011.vcf.gz`. ClinVar is public domain data from NCBI; its
source is `https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz`.
The NCBI HTTPS host also disallows all paths in robots.txt, so
`tools/fetch_public_data.sh` does not fetch ClinVar; to refresh it, use NCBI's
FTP protocol endpoint (`ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/`)
and check the published MD5.

## Total on disk

`du -sh` of the data folder after the fetch: 799 MB (all four samples,
reference, truth and stratifications), plus the shared 200 MB ClinVar VCF.

# Capacity planning

Part 1 is measured. Part 2 is a projection from those measurements to whole
genomes on a Slurm cluster; it is labelled as such and every assumption is
listed. Do not quote Part 2 numbers as measurements.

## Part 1: measured (2026-10-19)

Host: Mac Studio, Apple Silicon, 28 cores, 96 GB RAM; workflow limited to 8
cores and 24 GB, `nice -n 10`; native arm64 builds of every tool.

### Whole run, HG002, 3.8 Mb evaluation intervals, about 29x

Command: `nice -n 10 .venv/bin/python tools/snakemake_macos.py --profile profiles/local --forceall`
under `/usr/bin/time -l`.

| Quantity | Value | Source |
| --- | --- | --- |
| Input | 850,492 reads (2 x 148 bp), 100.6 MB gzipped FASTQ | `qc_summary.tsv`, `MANIFEST.tsv` |
| End-to-end wall time | 212.25 s | `/usr/bin/time` |
| CPU time, all processes | 366.7 s (323.8 user + 42.8 system) | `/usr/bin/time` |
| of which bwa index (once per reference) | 142.6 s CPU, 155.9 s wall | `profiling.by_rule.tsv` |
| CPU time per sample, excluding the index | about 224 s, 0.062 CPU-hours | difference of the two rows above |
| Jobs | 52 | Snakemake log |

### Per rule (from the benchmark directive)

| Rule | Jobs | Wall s (sum) | Longest job s | Peak RSS MB | Threads |
| --- | --- | --- | --- | --- | --- |
| bwa_index | 1 | 155.9 | 155.9 | 391 | 1 |
| fastp | 1 | 27.7 | 27.7 | 1,211 | 4 |
| bwa_mem | 1 | 19.0 | 19.0 | 1,208 | 8 |
| call_freebayes | 8 | 27.3 | 4.1 | 363 | 1 |
| call_bcftools | 8 | 20.1 | 3.1 | 185 | 1 |
| vcfeval | 2 | 6.4 | 3.5 | not sampled | 2 |
| stratified_metrics | 2 | 4.4 | 2.2 | 52 | 1 |
| markdup | 1 | 2.8 | 2.8 | 73 | 4 |
| mosdepth | 1 | 2.2 | 2.2 | 465 | 2 |
| samtools_stats | 1 | 1.6 | 1.6 | 17 | 2 |

"Not sampled": the job finished before Snakemake's sampler saw the tool
process, so only the shell wrapper (about 9 MB) was recorded. The same
applies to gather, normalise and annotate (each under 1 s). Peak RSS is a
sampled lower bound for every short job.

The bwa index files for chr13 and chr17 (197 Mb of sequence) total 346 MB;
bwa mem's 1,208 MB peak is mostly that index plus read batches of
`-K 100000000` bases.

### Scaling with region size

SCALING_TABLE

## Part 2: projection to hundreds of whole genomes (not measured)

### Assumptions

1. Per-sample CPU time scales linearly with the number of reads for fastp,
   alignment, duplicate marking and calling. A 30x whole genome of 2 x 148 bp
   reads has about 3.1e9 x 30 / 148 = 628 million reads, 739 times the
   850,492 reads measured here.
2. Alignment against the whole GRCh38 index (about 16 times more sequence
   than chr13 plus chr17) is slower per read than against this small index,
   because of more seed hits and cache misses. The projection does not model
   this, so it is a lower bound.
3. The cluster runs linux/amd64 with comparable per-core speed. That has not
   been measured; arm64 and x86 per-core throughput for bwa differ.
4. The bwa index is built once per reference and shared, so it is not part of
   the per-sample cost.

### Projected per-genome cost (lower bound)

0.062 CPU-hours per sample x 739 = about 46 CPU-hours per 30x genome for this
pipeline with two callers. Published whole-genome runs of bwa mem alone are
usually reported well above this, which is what assumption 2 predicts; treat
46 as a floor and replace it with a measured whole-chromosome run (ROADMAP)
before ordering hardware.

Memory per job is set by the index, not the sample: about 1.2 GB here for a
197 Mb reference. Expect bwa mem on whole GRCh38 to need several GB; the
`mem_mb` function in `common.smk` scales with input size, which includes the
index files, and grows 1.5 times per retry.

### Projected cohort: 500 genomes

| Quantity | Projection |
| --- | --- |
| CPU-hours | 500 x 46 = 23,000 (floor) |
| Wall time on 1,000 cores, perfectly packed | about 23 hours (floor) |
| Calling jobs at 500 kb chunks | about 6,200 per genome per caller: too many |
| Calling jobs at 20 Mb chunks | about 155 per genome per caller |

### What changes for whole genomes on Slurm

* Chunk size. At 500 kb a whole genome gives about 6,200 calling jobs per
  caller, each a few seconds of work; Slurm scheduling overhead would dominate.
  Set `scatter.chunk_size` to 10 to 20 Mb for whole genomes, or use Snakemake
  job grouping (`--groups call_bcftools=calls --group-components calls=50`)
  so one Slurm job runs many chunks.
* Retries. Keep `retries: 2` in the Slurm profile; the resource functions give
  1.5 times the memory and twice the runtime on each attempt.
* Before, during and after submission. Before: `snakemake -n` for job counts
  and `--rulegraph` for the shape; a test-profile run for environment builds.
  During: `squeue -u $USER`, `sstat -j <jobid> --format=MaxRSS,AveCPU` for
  running jobs, rule logs under `logs/`. After: `sacct -j <jobid>
  --format=JobID,State,Elapsed,MaxRSS,ReqMem,AllocCPUS` against the
  `benchmarks/` files, and adjust the coefficients in `common.smk` when
  requested memory is far above the measured peak.
* Storage. Per sample this run kept a 79 MB duplicate-marked BAM for the two
  2 Mb windows; scaled by reads that is about 58 GB per 30x genome
  (projection). Temporary
  outputs (trimmed FASTQ, unsorted BAM, per-chunk VCFs) are marked `temp()`
  and removed as soon as no job needs them.

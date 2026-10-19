import os

import pandas as pd
from snakemake.utils import validate

validate(config, schema="../schemas/config.schema.yaml")

samples = (
    pd.read_csv(config["samples"], sep="\t", dtype=str, comment="#")
    .set_index("sample", drop=False)
    .sort_index()
)
validate(samples, schema="../schemas/samples.schema.yaml")

SAMPLES = list(samples.index)
CALLERS = list(config["callers"])
STRATA = list(config["evaluation"]["stratifications"])


wildcard_constraints:
    sample="|".join(SAMPLES),
    caller="|".join(CALLERS),
    chunk=r"\d{4}",
    stratum="|".join(STRATA),


# ---------------------------------------------------------------- input functions


def get_fastqs(wildcards):
    row = samples.loc[wildcards.sample]
    return {"r1": row["fq1"], "r2": row["fq2"]}


def get_truth(wildcards):
    row = samples.loc[wildcards.sample]
    return {"vcf": row["truth_vcf"], "bed": row["truth_bed"]}


def has_truth(sample):
    row = samples.loc[sample]
    return isinstance(row.get("truth_vcf"), str) and row["truth_vcf"] != ""


def read_group(wildcards):
    # One library per sample in this samplesheet; the platform unit is fixed
    # because the reads were re-derived from a merged BAM.
    s = wildcards.sample
    return rf"@RG\tID:{s}\tSM:{s}\tLB:{s}\tPL:ILLUMINA\tPU:{s}.1"


def scatter_chunks(wildcards):
    """Chunk ids produced by the scatter checkpoint (known only after it runs)."""
    outdir = checkpoints.scatter_intervals.get().output[0]
    return sorted(glob_wildcards(f"{outdir}/{{chunk}}.bed").chunk)


def gathered_chunks(wildcards):
    # The .tbi files are listed as inputs too: they are temp() outputs of the
    # calling rules, and a temp file that no job declares as input is deleted
    # as soon as it is written.
    chunks = scatter_chunks(wildcards)
    pattern = "results/calls/{sample}/{caller}/chunks/{chunk}.vcf.gz"
    vcfs = expand(
        pattern, sample=wildcards.sample, caller=wildcards.caller, chunk=chunks
    )
    return {"vcfs": vcfs, "tbis": [f"{v}.tbi" for v in vcfs]}


# ------------------------------------------------------------- resource functions
# Memory and runtime scale with the size of the main input and grow on each
# retry, so a job killed for memory on attempt 1 is resubmitted with more.
# Coefficients come from the benchmark tables of the runs in docs/validation.md.


def mem_mb(base, per_gb=0, growth=1.5, cap=64000):
    def _mem(wildcards, input, attempt):
        size_gb = input.size_mb / 1024
        return int(min(cap, (base + per_gb * size_gb) * growth ** (attempt - 1)))

    return _mem


def runtime_min(base, per_gb=0, growth=2.0):
    def _runtime(wildcards, input, attempt):
        size_gb = input.size_mb / 1024
        return int((base + per_gb * size_gb) * growth ** (attempt - 1))

    return _runtime


# -------------------------------------------------------------------- targets


def all_targets():
    targets = [
        "results/report/accuracy.tsv",
        "results/report/profiling.tsv",
        "results/report/accuracy_f1.svg",
        "results/report/runtime.svg",
        "results/report/clinvar_summary.tsv",
        "results/qc/qc_summary.tsv",
    ]
    targets += expand(
        "results/annotated/{sample}/{caller}.clinvar.vcf.gz",
        sample=SAMPLES,
        caller=CALLERS,
    )
    return targets


def evaluated_pairs():
    return [(s, c) for s in SAMPLES if has_truth(s) for c in CALLERS]

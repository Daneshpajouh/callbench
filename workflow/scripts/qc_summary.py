"""One row per sample from fastp JSON, samtools stats and mosdepth summaries."""

import json
from typing import Any

import pandas as pd


def fastp_metrics(path: str) -> dict[str, float]:
    with open(path) as fh:
        d = json.load(fh)
    before = d["summary"]["before_filtering"]
    after = d["summary"]["after_filtering"]
    return {
        "reads_raw": before["total_reads"],
        "reads_after_fastp": after["total_reads"],
        "q30_rate_after": round(after["q30_rate"], 4),
        "duplication_rate_fastp": round(d.get("duplication", {}).get("rate", float("nan")), 4),
    }


def samtools_sn(path: str) -> dict[str, float]:
    wanted = {
        "reads mapped:": "reads_mapped",
        "reads duplicated:": "reads_duplicated",
        "error rate:": "error_rate",
        "insert size average:": "insert_size_mean",
        "reads properly paired:": "reads_properly_paired",
    }
    out: dict[str, float] = {}
    with open(path) as fh:
        for line in fh:
            if not line.startswith("SN\t"):
                continue
            _, key, value = line.rstrip("\n").split("\t")[:3]
            if key in wanted:
                out[wanted[key]] = float(value)
    return out


def mosdepth_mean(path: str) -> dict[str, float]:
    df = pd.read_csv(path, sep="\t")
    region_rows = df[df["chrom"] == "total_region"]
    row = region_rows.iloc[0] if len(region_rows) else df[df["chrom"] == "total"].iloc[0]
    return {"mean_depth_regions": round(float(row["mean"]), 2)}


def main(smk: Any) -> None:
    rows = []
    for sample, fp, st, md in zip(
        smk.params.samples, smk.input.fastp, smk.input.stats, smk.input.mosdepth, strict=True
    ):
        row: dict[str, Any] = {"sample": sample}
        row.update(fastp_metrics(fp))
        row.update(samtools_sn(st))
        row.update(mosdepth_mean(md))
        rows.append(row)
    pd.DataFrame(rows).to_csv(smk.output[0], sep="\t", index=False)


if "snakemake" in globals():
    main(globals()["snakemake"])

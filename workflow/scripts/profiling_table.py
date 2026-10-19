"""Turn the files written by Snakemake's benchmark directive into one table.

Benchmark files live at benchmarks/<rule>/<wildcards>.tsv (or
benchmarks/<rule>.tsv for rules without wildcards). Columns kept: wall time
(s), peak resident memory (max_rss, MB), CPU time (s) and mean load.
Scattered rules are also summed per sample so the cost of one genome is
visible next to the cost of one chunk.
"""

from pathlib import Path
from typing import Any

import pandas as pd

KEEP = ["s", "max_rss", "cpu_time", "mean_load", "io_in", "io_out"]


def collect(benchmark_dir: str | Path) -> pd.DataFrame:
    rows = []
    root = Path(benchmark_dir)
    for f in sorted(root.rglob("*.tsv")):
        rel = f.relative_to(root)
        rule = rel.parts[0].removesuffix(".tsv")
        job = rel.stem if len(rel.parts) > 1 else ""
        df = pd.read_csv(f, sep="\t")
        for _, r in df.iterrows():
            row: dict[str, Any] = {"rule": rule, "job": job}
            for k in KEEP:
                row[k] = r.get(k)
            rows.append(row)
    out = pd.DataFrame(rows, columns=["rule", "job", *KEEP])
    out["sample"] = out["job"].str.split(".").str[0]
    return out


def per_rule_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("rule")
    return pd.DataFrame(
        {
            "jobs": g.size(),
            "wall_s_total": g["s"].sum().round(1),
            "wall_s_max": g["s"].max().round(1),
            "cpu_s_total": g["cpu_time"].sum().round(1),
            "max_rss_mb_peak": g["max_rss"].max().round(1),
        }
    ).reset_index()


def main(smk: Any) -> None:
    df = collect(smk.params.benchmark_dir)
    df.to_csv(smk.output.table, sep="\t", index=False)
    summary = per_rule_summary(df)
    summary.to_csv(smk.output.by_rule, sep="\t", index=False)
    with open(smk.log[0], "w") as log:
        print(summary.to_string(index=False), file=log)


if "snakemake" in globals():
    main(globals()["snakemake"])

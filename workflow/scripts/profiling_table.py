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
from logsetup import log_failures, read_tsv, rule_logger

KEEP = ["s", "max_rss", "cpu_time", "mean_load", "io_in", "io_out"]


def collect(benchmark_dir: str | Path) -> pd.DataFrame:
    rows = []
    root = Path(benchmark_dir)
    for f in sorted(root.rglob("*.tsv")):
        rel = f.relative_to(root)
        rule = rel.parts[0].removesuffix(".tsv")
        job = rel.stem if len(rel.parts) > 1 else ""
        df = read_tsv(f)
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
            # min_count=1 keeps NA when no job reported CPU time (macOS without the
            # psutil shim); a plain sum would report 0.0 s for work that ran.
            "cpu_s_total": g["cpu_time"].sum(min_count=1).round(1),
            "max_rss_mb_peak": g["max_rss"].max().round(1),
        }
    ).reset_index()


def main(smk: Any) -> None:
    log = rule_logger(smk)
    with log_failures(log):
        df = collect(smk.params.benchmark_dir)
        log.info("read %d benchmark records from %s", len(df), smk.params.benchmark_dir)
        df.to_csv(smk.output.table, sep="\t", index=False)
        summary = per_rule_summary(df)
        summary.to_csv(smk.output.by_rule, sep="\t", index=False)
        log.info(
            "wrote %d records to %s and %d rules to %s",
            len(df),
            smk.output.table,
            len(summary),
            smk.output.by_rule,
        )
        log.debug("per-rule summary:\n%s", summary.to_string(index=False))


if "snakemake" in globals():
    main(globals()["snakemake"])

"""Two figures for the report: F1 by caller and stratum, and runtime by rule."""

from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def f1_figure(acc: pd.DataFrame, out: str) -> None:
    acc = acc.copy()
    acc["f1"] = pd.to_numeric(acc["f1"], errors="coerce")
    types = ["SNV", "INDEL"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, vtype in zip(axes, types, strict=True):
        sub = acc[acc["type"] == vtype]
        pivot = sub.pivot_table(index="stratum", columns="caller", values="f1", aggfunc="mean")
        if pivot.empty:
            # pivot_table drops all-NA columns, and pandas refuses to draw an empty
            # frame. A panel with no F1 values (no indels in a small slice) still
            # needs to render so the report build does not fail.
            ax.text(0.5, 0.5, "no F1 values", ha="center", va="center", transform=ax.transAxes)
        else:
            pivot.plot.bar(ax=ax, rot=30)
        ax.set_title(f"{vtype} F1 (mean over samples)")
        ax.set_ylim(0, 1)
        ax.set_xlabel("")
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("F1")
    fig.tight_layout()
    fig.savefig(out)


def runtime_figure(by_rule: pd.DataFrame, out: str) -> None:
    df = by_rule.sort_values("wall_s_total")
    fig, ax = plt.subplots(figsize=(8, max(3, 0.3 * len(df))))
    ax.barh(df["rule"], df["wall_s_total"])
    ax.set_xlabel("wall time summed over jobs (s)")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out)


def main(smk: Any) -> None:
    f1_figure(pd.read_csv(smk.input.accuracy, sep="\t"), smk.output.f1)
    runtime_figure(pd.read_csv(smk.input.profiling, sep="\t"), smk.output.runtime)


if "snakemake" in globals():
    main(globals()["snakemake"])

"""Count ClinVar-matched calls by clinical significance, per sample and caller."""

from pathlib import Path
from typing import Any

import pandas as pd


def summarise(paths: list[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        df = pd.read_csv(p, sep="\t", dtype=str)
        caller = Path(p).name.split(".")[0]
        sample = Path(p).parent.name
        df["sample"], df["caller"] = sample, caller
        frames.append(df)
    allcalls = pd.concat(frames, ignore_index=True)
    if allcalls.empty:
        return pd.DataFrame(columns=["sample", "caller", "clnsig", "calls"])
    return (
        allcalls.groupby(["sample", "caller", "clnsig"])
        .size()
        .rename("calls")
        .reset_index()
        .sort_values(["sample", "caller", "calls"], ascending=[True, True, False])
    )


def main(smk: Any) -> None:
    summarise(list(smk.input)).to_csv(smk.output[0], sep="\t", index=False)


if "snakemake" in globals():
    main(globals()["snakemake"])

"""Concatenate per-sample, per-caller TSVs that share one header."""

from typing import Any

import pandas as pd


def concat_tsvs(paths: list[str]) -> pd.DataFrame:
    frames = [pd.read_csv(p, sep="\t") for p in paths]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def main(smk: Any) -> None:
    concat_tsvs(list(smk.input)).to_csv(smk.output[0], sep="\t", index=False)


if "snakemake" in globals():
    main(globals()["snakemake"])

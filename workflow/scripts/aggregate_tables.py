"""Concatenate per-sample, per-caller TSVs that share one header."""

from typing import Any

import pandas as pd
from logsetup import log_failures, read_tsv, rule_logger


def concat_tsvs(paths: list[str]) -> pd.DataFrame:
    frames = [read_tsv(p) for p in paths]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def main(smk: Any) -> None:
    log = rule_logger(smk)
    with log_failures(log):
        log.info("reading %d tables", len(smk.input))
        table = concat_tsvs(list(smk.input))
        table.to_csv(smk.output[0], sep="\t", index=False)
        log.info("wrote %d rows, %d columns to %s", len(table), len(table.columns), smk.output[0])


if "snakemake" in globals():
    main(globals()["snakemake"])

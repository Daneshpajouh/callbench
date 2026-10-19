"""Count ClinVar-matched calls by clinical significance, per sample and caller."""

from pathlib import Path
from typing import Any

import pandas as pd
from logsetup import log_failures, read_tsv, rule_logger


def summarise(paths: list[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        df = read_tsv(p, as_str=True)
        caller = Path(p).name.split(".")[0]
        sample = Path(p).parent.name
        df["sample"], df["caller"] = sample, caller
        frames.append(df)
    # pd.concat raises on an empty list; no input tables means no calls.
    allcalls = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
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
    log = rule_logger(smk)
    with log_failures(log):
        log.info("reading %d ClinVar tables", len(smk.input))
        summary = summarise(list(smk.input))
        summary.to_csv(smk.output[0], sep="\t", index=False)
        log.info(
            "wrote %d rows covering %d calls to %s",
            len(summary),
            int(summary["calls"].sum()),
            smk.output[0],
        )


if "snakemake" in globals():
    main(globals()["snakemake"])

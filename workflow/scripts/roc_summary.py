"""Best F1 and recall at a fixed precision from vcfeval ROC tables.

One QUAL cut compares two callers at one point on two differently scaled
scores, so part of an F1 gap at that cut is the choice of cut. vcfeval run with
``--vcf-score-field QUAL`` on unfiltered calls writes a ROC table per variant
class (snp_roc.tsv.gz, non_snp_roc.tsv.gz): one row per score threshold with
cumulative counts. This script reads the counts, recomputes recall and
precision from them, and reports for each caller the best F1 over all
thresholds and the recall at a target precision. The deployed filter in
config/config.yaml is unchanged; this is a comparison, not a new filter.
"""

import gzip
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from logsetup import log_failures, rule_logger

ROC_FILES = {"SNV": "snp_roc.tsv.gz", "INDEL": "non_snp_roc.tsv.gz"}

# vcfeval has named the call-side true positive column both ways across releases.
COLUMNS = {
    "score": ("score",),
    "tp_base": ("true_positives_baseline",),
    "fp": ("false_positives",),
    "tp_call": ("true_positives_call", "true_positives"),
    "fn": ("false_negatives",),
}

SUMMARY_COLUMNS = [
    "sample",
    "caller",
    "type",
    "best_f1",
    "best_f1_score",
    "target_precision",
    "recall_at_target",
    "score_at_target",
]


def read_roc(path: str | Path) -> pd.DataFrame:
    """Read a vcfeval ROC table into score, tp_base, fn, tp_call and fp columns."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as fh:
        lines = fh.read().splitlines()
    # RTG Tools 3.13 writes a "#score field: QUAL" line before the column header.
    header = next((ln for ln in lines if ln.startswith("#score\t")), None)
    if header is None:
        raise ValueError(f"{path}: no '#score' header line")
    names = header.lstrip("#").split("\t")
    rows = [ln.split("\t") for ln in lines if ln and not ln.startswith("#")]
    raw = pd.DataFrame(rows, columns=names)
    out = {}
    for key, options in COLUMNS.items():
        found = next((o for o in options if o in raw.columns), None)
        if found is None:
            raise ValueError(f"{path}: none of {options} in header {names}")
        out[key] = pd.to_numeric(raw[found])
    return pd.DataFrame(out)


def summarise(roc: pd.DataFrame, target_precision: float) -> dict[str, float | None]:
    """Best F1 over thresholds, and the highest recall whose precision meets the target."""
    truth = roc["tp_base"] + roc["fn"]
    called = roc["tp_call"] + roc["fp"]
    recall = (roc["tp_base"] / truth).where(truth > 0)
    precision = (roc["tp_call"] / called).where(called > 0)
    f1 = (2 * precision * recall / (precision + recall)).where((precision + recall) > 0)
    result: dict[str, float | None] = {
        "best_f1": None,
        "best_f1_score": None,
        "recall_at_target": None,
        "score_at_target": None,
    }
    f1_v = f1.to_numpy(dtype=float)
    recall_v = recall.to_numpy(dtype=float)
    scores = roc["score"].to_numpy(dtype=float)
    if not np.isnan(f1_v).all():
        i = int(np.nanargmax(f1_v))
        result["best_f1"] = float(f1_v[i])
        result["best_f1_score"] = float(scores[i])
    meets = np.flatnonzero((precision >= target_precision - 1e-12).to_numpy() & ~np.isnan(recall_v))
    if meets.size:
        j = int(meets[np.argmax(recall_v[meets])])
        result["recall_at_target"] = float(recall_v[j])
        result["score_at_target"] = float(scores[j])
    return result


def summary_table(pairs: list[tuple[str, str, str]], target_precision: float) -> pd.DataFrame:
    """One row per (sample, caller, type) from (sample, caller, vcfeval directory) pairs."""
    rows: list[dict[str, Any]] = []
    for sample, caller, outdir in pairs:
        for vtype, name in ROC_FILES.items():
            s = summarise(read_roc(Path(outdir) / name), target_precision)
            rows.append(
                {
                    "sample": sample,
                    "caller": caller,
                    "type": vtype,
                    "target_precision": target_precision,
                    **s,
                }
            )
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)


def main(smk: Any) -> None:
    log = rule_logger(smk)
    with log_failures(log):
        pairs = list(zip(smk.params.samples, smk.params.callers, smk.params.dirs, strict=True))
        table = summary_table(pairs, float(smk.params.target_precision))
        table.to_csv(smk.output[0], sep="\t", index=False, float_format="%.4f")
        log.info("wrote %d ROC summary rows to %s", len(table), smk.output[0])


if "snakemake" in globals():
    main(globals()["snakemake"])
elif __name__ == "__main__" and len(sys.argv) == 3:
    print(pd.Series(summarise(read_roc(sys.argv[1]), float(sys.argv[2]))).to_string())

import gzip
from pathlib import Path

import pandas as pd
import pytest
from roc_summary import SUMMARY_COLUMNS, read_roc, summarise, summary_table
from smk_stub import make_smk, run_as_rule_script

HEADER = (
    "#score\ttrue_positives_baseline\tfalse_positives\ttrue_positives_call"
    "\tfalse_negatives\tprecision\tsensitivity\tf_measure"
)

# Cumulative counts at falling QUAL thresholds for a truth set of 100 variants.
# Lowering the threshold gains true positives and then mostly false positives.
ROWS = [
    (60.0, 50, 0, 50, 50),
    (40.0, 80, 1, 80, 20),
    (20.0, 95, 5, 95, 5),
    (5.0, 98, 30, 98, 2),
]


def _write(path: Path, rows: list[tuple[float, int, int, int, int]], header: str = HEADER) -> Path:
    lines = ["#Version 3.13", "#CMD line", header]
    lines += [f"{s}\t{tb}\t{fp}\t{tc}\t{fn}\t0\t0\t0" for s, tb, fp, tc, fn in rows]
    with gzip.open(path, "wt") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def test_read_roc_takes_counts_from_the_named_columns(tmp_path: Path) -> None:
    roc = read_roc(_write(tmp_path / "snp_roc.tsv.gz", ROWS))
    assert list(roc.columns) == ["score", "tp_base", "fp", "tp_call", "fn"]
    assert roc["fp"].tolist() == [0, 1, 5, 30]
    assert roc["fn"].tolist() == [50, 20, 5, 2]


def test_read_roc_accepts_the_older_true_positives_name(tmp_path: Path) -> None:
    header = HEADER.replace("true_positives_call", "true_positives")
    roc = read_roc(_write(tmp_path / "r.tsv.gz", ROWS, header))
    assert roc["tp_call"].tolist() == [50, 80, 95, 98]


def test_read_roc_refuses_a_table_without_the_header(tmp_path: Path) -> None:
    path = tmp_path / "bad.tsv.gz"
    with gzip.open(path, "wt") as fh:
        fh.write("60\t1\t0\t1\t0\n")
    with pytest.raises(ValueError, match="#score"):
        read_roc(path)


def test_read_roc_refuses_a_missing_count_column(tmp_path: Path) -> None:
    header = HEADER.replace("false_negatives", "something_else")
    with pytest.raises(ValueError, match="false_negatives"):
        read_roc(_write(tmp_path / "r.tsv.gz", ROWS, header))


def test_best_f1_is_the_maximum_over_thresholds(tmp_path: Path) -> None:
    s = summarise(read_roc(_write(tmp_path / "r.tsv.gz", ROWS)), 0.99)
    # At QUAL 20: recall 0.95, precision 0.95, F1 0.95; no other row is higher.
    assert s["best_f1"] == pytest.approx(0.95)
    assert s["best_f1_score"] == 20.0


def test_recall_at_target_precision_takes_the_lowest_qualifying_threshold(tmp_path: Path) -> None:
    roc = read_roc(_write(tmp_path / "r.tsv.gz", ROWS))
    # Precision 1.0 at 60 and 80/81 at 40 (0.9877); only 60 meets 0.99, 40 meets 0.98.
    assert summarise(roc, 0.99)["recall_at_target"] == pytest.approx(0.50)
    assert summarise(roc, 0.98)["recall_at_target"] == pytest.approx(0.80)
    assert summarise(roc, 0.98)["score_at_target"] == 40.0


def test_unreachable_target_gives_no_recall(tmp_path: Path) -> None:
    rows = [(30.0, 9, 1, 9, 1)]
    s = summarise(read_roc(_write(tmp_path / "r.tsv.gz", rows)), 0.99)
    assert s["recall_at_target"] is None and s["score_at_target"] is None
    assert s["best_f1"] == pytest.approx(0.9)


def test_empty_table_gives_no_values(tmp_path: Path) -> None:
    s = summarise(read_roc(_write(tmp_path / "r.tsv.gz", [])), 0.99)
    assert all(v is None for v in s.values())


def test_summary_table_has_one_row_per_pair_and_type(tmp_path: Path) -> None:
    for caller in ("bcftools", "freebayes"):
        d = tmp_path / caller
        d.mkdir()
        _write(d / "snp_roc.tsv.gz", ROWS)
        _write(d / "non_snp_roc.tsv.gz", ROWS[:2])
    pairs = [("HG002", c, str(tmp_path / c)) for c in ("bcftools", "freebayes")]
    table = summary_table(pairs, 0.99)
    assert list(table.columns) == SUMMARY_COLUMNS
    assert len(table) == 4
    indel = table[(table.caller == "freebayes") & (table.type == "INDEL")].iloc[0]
    assert indel["best_f1"] == pytest.approx(2 * (80 / 81) * 0.8 / ((80 / 81) + 0.8))


def test_rule_script_writes_the_summary(tmp_path: Path) -> None:
    d = tmp_path / "roc"
    d.mkdir()
    _write(d / "snp_roc.tsv.gz", ROWS)
    _write(d / "non_snp_roc.tsv.gz", ROWS)
    out = tmp_path / "roc_summary.tsv"
    smk = make_smk(
        tmp_path,
        "roc_summary",
        output=[str(out)],
        params=type(
            "P",
            (),
            {"samples": ["HG002"], "callers": ["bcftools"], "dirs": [str(d)],
             "target_precision": 0.99},
        )(),
    )
    run_as_rule_script("roc_summary", smk)
    table = pd.read_csv(out, sep="\t")
    assert table["type"].tolist() == ["SNV", "INDEL"]
    assert table["best_f1"].tolist() == [0.95, 0.95]

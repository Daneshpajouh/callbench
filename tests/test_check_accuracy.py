import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from check_accuracy import compare


def _table(f1: str) -> pd.DataFrame:
    return pd.DataFrame(
        [{"sample": "HG002", "caller": "bcftools", "stratum": "all", "type": "SNV", "f1": f1}]
    )


def test_drop_beyond_tolerance_is_a_regression() -> None:
    assert compare(_table("0.9800"), _table("0.9900"), 0.005)


def test_small_change_and_gain_pass() -> None:
    assert compare(_table("0.9880"), _table("0.9900"), 0.005) == []
    assert compare(_table("0.9950"), _table("0.9900"), 0.005) == []


def test_missing_row_is_a_regression() -> None:
    assert compare(_table("NA"), _table("0.9900"), 0.005)

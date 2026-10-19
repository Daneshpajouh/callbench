import pytest
from stratified_metrics import Counts, fmt


def test_counts_follow_ga4gh_definitions() -> None:
    c = Counts(tp_base=90, fn=10, tp_call=88, fp=12)
    assert c.recall == pytest.approx(0.9)
    assert c.precision == pytest.approx(0.88)
    assert c.f1 == pytest.approx(2 * 0.9 * 0.88 / (0.9 + 0.88))


def test_empty_stratum_gives_na_not_zero() -> None:
    c = Counts(tp_base=0, fn=0, tp_call=0, fp=0)
    assert c.recall is None and c.precision is None and c.f1 is None
    assert fmt(c.f1) == "NA"


def test_all_false_positives() -> None:
    c = Counts(tp_base=0, fn=5, tp_call=0, fp=3)
    assert c.recall == 0 and c.precision == 0 and c.f1 is None

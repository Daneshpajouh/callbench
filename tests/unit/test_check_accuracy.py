import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest
from check_accuracy import compare, main
from smk_stub import DATA, ROOT

COLUMNS = ["sample", "caller", "stratum", "type", "f1"]


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


@pytest.mark.parametrize(
    ("observed", "expected", "tolerance", "regressions"),
    [
        pytest.param("0.9900", "0.9900", 0.005, 0, id="identical"),
        pytest.param("0.9851", "0.9900", 0.005, 0, id="inside-tolerance"),
        pytest.param("0.9849", "0.9900", 0.005, 1, id="just-outside-tolerance"),
        pytest.param(
            "0.4956", "0.5006", 0.005, 0, id="drop-of-exactly-tolerance-is-not-a-regression"
        ),
        pytest.param("0.4955", "0.5006", 0.005, 1, id="one-unit-more-than-tolerance"),
        pytest.param("0.9899", "0.9900", 0.0, 1, id="zero-tolerance-flags-any-drop"),
        pytest.param("0.9900", "0.9900", 0.0, 0, id="zero-tolerance-allows-equal"),
        pytest.param("0.0000", "0.0000", 0.005, 0, id="both-zero"),
        pytest.param("0.0000", "1.0000", 0.005, 1, id="collapse-to-zero"),
        pytest.param("1.0000", "0.0000", 0.005, 0, id="gain-from-zero"),
        pytest.param("NA", "NA", 0.005, 0, id="both-na"),
        pytest.param("0.5000", "NA", 0.005, 0, id="expected-na-is-skipped"),
        pytest.param("NA", "0.5000", 0.005, 1, id="observed-na-is-a-regression"),
        pytest.param("", "0.5000", 0.005, 1, id="observed-blank-is-a-regression"),
        pytest.param("not-a-number", "0.5000", 0.005, 1, id="observed-text-is-a-regression"),
        pytest.param("0.5000", "not-a-number", 0.005, 0, id="expected-text-is-skipped"),
    ],
)
def test_compare_edge_cases(
    observed: str, expected: str, tolerance: float, regressions: int
) -> None:
    assert len(compare(_table(observed), _table(expected), tolerance)) == regressions


def test_regression_message_names_the_row_and_both_values() -> None:
    (problem,) = compare(_table("0.9000"), _table("0.9500"), 0.005)
    assert problem == "HG002/bcftools/all/SNV: F1 0.9000 < expected 0.9500"


def test_missing_row_message() -> None:
    (problem,) = compare(_table("NA"), _table("0.9500"), 0.005)
    assert problem == "HG002/bcftools/all/SNV: missing or NA in observed table"


def test_numeric_f1_columns_are_accepted() -> None:
    observed, expected = _table("0.9").assign(f1=0.9), _table("0.95").assign(f1=0.95)
    assert len(compare(observed, expected, 0.005)) == 1


def test_row_absent_from_observed_is_a_regression() -> None:
    observed = _table("0.9900").assign(sample="HG003")
    (problem,) = compare(observed, _table("0.9900"), 0.005)
    assert problem.startswith("HG002/bcftools/all/SNV: missing")


def test_extra_observed_rows_are_ignored() -> None:
    observed = pd.concat([_table("0.9900"), _table("0.1000").assign(type="INDEL")])
    assert compare(observed, _table("0.9900"), 0.005) == []


def test_empty_expected_table_has_nothing_to_regress() -> None:
    assert compare(_table("0.5"), pd.DataFrame(columns=COLUMNS), 0.005) == []


def test_empty_observed_table_regresses_every_expected_row() -> None:
    assert len(compare(pd.DataFrame(columns=COLUMNS), _table("0.9900"), 0.005)) == 1


def test_duplicate_observed_rows_are_each_checked() -> None:
    observed = pd.concat([_table("0.9900"), _table("0.5000")])
    assert len(compare(observed, _table("0.9900"), 0.005)) == 1


def test_change_within_tolerance_is_reported_on_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    assert compare(_table("0.9880"), _table("0.9900"), 0.005) == []
    assert "F1 changed 0.9900 -> 0.9880 (within tolerance)" in capsys.readouterr().out


def test_unchanged_value_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    compare(_table("0.9900"), _table("0.9900"), 0.005)
    assert capsys.readouterr().out == ""


def test_main_with_na_in_both_tables(capsys: pytest.CaptureFixture[str]) -> None:
    observed, expected = DATA / "accuracy_observed_with_na.tsv", DATA / "accuracy_expected.tsv"
    # The observed INDEL row is NA where F1 0.8 was expected: one regression. The SNV
    # row dropped from 0.90 to 0.89, which is outside 0.005 as well.
    assert main([str(observed), str(expected)]) == 1
    err = capsys.readouterr().err
    assert "REGRESSION HG002/bcftools/all/INDEL: missing or NA in observed table" in err
    assert "REGRESSION HG002/bcftools/all/SNV: F1 0.8900 < expected 0.9000" in err
    assert "low_complexity" not in err


def test_main_tolerance_option_widens_the_gate(capsys: pytest.CaptureFixture[str]) -> None:
    observed = DATA / "accuracy_observed_with_na.tsv"
    expected = DATA / "accuracy_expected.tsv"
    assert main([str(observed), str(expected), "--tolerance", "0.02"]) == 1
    err = capsys.readouterr().err
    assert "SNV" not in err and "INDEL" in err


def test_main_returns_zero_for_a_table_compared_with_itself(tmp_path: Path) -> None:
    table = DATA / "accuracy_expected.tsv"
    assert main([str(table), str(table)]) == 0


def test_main_reads_tab_separated_files(tmp_path: Path) -> None:
    obs, exp = tmp_path / "o.tsv", tmp_path / "e.tsv"
    header = "sample\tcaller\tstratum\ttype\tf1\n"
    obs.write_text(header + "HG002\tbcftools\tall\tSNV\t0.9\n")
    exp.write_text(header + "HG002\tbcftools\tall\tSNV\t0.9\n")
    assert main([str(obs), str(exp)]) == 0


def test_main_requires_both_files(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["only-one.tsv"])
    assert info.value.code == 2
    assert "expected" in capsys.readouterr().err


def test_script_exit_status_is_the_regression_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    table = str(DATA / "accuracy_expected.tsv")
    monkeypatch.setattr(sys, "argv", ["check_accuracy.py", table, table])
    with pytest.raises(SystemExit) as info:
        runpy.run_path(str(ROOT / "tools" / "check_accuracy.py"), run_name="__main__")
    assert info.value.code == 0

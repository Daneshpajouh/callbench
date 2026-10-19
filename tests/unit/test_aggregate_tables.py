from pathlib import Path

import pytest
from aggregate_tables import concat_tsvs
from smk_stub import DATA, make_smk, run_as_rule_script


def _tsv(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_bytes(text.encode())
    return str(path)


def test_no_inputs_gives_an_empty_table() -> None:
    assert concat_tsvs([]).empty


@pytest.mark.parametrize(
    ("texts", "rows", "columns"),
    [
        pytest.param(["a\tb\n1\t2\n"], 1, ["a", "b"], id="single-table"),
        pytest.param(["a\tb\n"], 0, ["a", "b"], id="header-only"),
        pytest.param(["a\tb\n", "a\tb\n"], 0, ["a", "b"], id="two-header-only-tables"),
        pytest.param(["a\tb\n", "a\tb\n1\t2\n"], 1, ["a", "b"], id="header-only-then-data"),
        pytest.param(["a\tb\n1\t2\n", "b\ta\n4\t3\n"], 2, ["a", "b"], id="columns-matched-by-name"),
        pytest.param(
            ["a\tb\n1\t2\n", "a\tc\n3\t4\n"], 2, ["a", "b", "c"], id="different-columns-union"
        ),
        pytest.param(["a\tb\r\n1\t2\r\n", "a\tb\r\n3\t4\r\n"], 2, ["a", "b"], id="crlf"),
        pytest.param(["a\tb\n1\tNA\n"], 1, ["a", "b"], id="na-value"),
    ],
)
def test_concat_edge_cases(tmp_path: Path, texts: list[str], rows: int, columns: list[str]) -> None:
    paths = [_tsv(tmp_path, f"{i}.tsv", t) for i, t in enumerate(texts)]
    out = concat_tsvs(paths)
    assert len(out) == rows
    assert list(out.columns) == columns


def test_concat_resets_the_index_and_keeps_order(tmp_path: Path) -> None:
    out = concat_tsvs([_tsv(tmp_path, "1.tsv", "a\n1\n2\n"), _tsv(tmp_path, "2.tsv", "a\n3\n")])
    assert list(out.index) == [0, 1, 2]
    assert list(out["a"]) == [1, 2, 3]


def test_concat_na_value_is_missing() -> None:
    out = concat_tsvs([str(DATA / "accuracy_observed_with_na.tsv")])
    assert out["f1"].isna().sum() == 2


def test_concat_empty_file_error_names_the_file(tmp_path: Path) -> None:
    empty = _tsv(tmp_path, "empty.tsv", "")
    with pytest.raises(ValueError, match=r"empty\.tsv: empty file"):
        concat_tsvs([_tsv(tmp_path, "ok.tsv", "a\n1\n"), empty])


def test_concat_malformed_error_names_the_file_and_line(tmp_path: Path) -> None:
    bad = _tsv(tmp_path, "bad.tsv", "a\tb\n1\t2\n3\t4\t5\t6\n")
    with pytest.raises(ValueError, match=r"bad\.tsv: malformed TSV.*line 3"):
        concat_tsvs([bad])


def test_rule_script_writes_a_tsv_without_an_index(tmp_path: Path) -> None:
    smk = make_smk(
        tmp_path,
        "aggregate_accuracy",
        input=[_tsv(tmp_path, "1.tsv", "a\tb\n1\t2\n"), _tsv(tmp_path, "2.tsv", "a\tb\n3\t4\n")],
        output=[str(tmp_path / "out.tsv")],
    )
    run_as_rule_script("aggregate_tables", smk)
    assert (tmp_path / "out.tsv").read_text() == "a\tb\n1\t2\n3\t4\n"
    log = (tmp_path / "aggregate_accuracy.log").read_text()
    assert "reading 2 tables" in log and "wrote 2 rows, 2 columns" in log


def test_rule_script_failure_is_logged_with_the_file(tmp_path: Path) -> None:
    smk = make_smk(
        tmp_path,
        "aggregate_accuracy",
        input=[_tsv(tmp_path, "empty.tsv", "")],
        output=[str(tmp_path / "out.tsv")],
    )
    with pytest.raises(ValueError):
        run_as_rule_script("aggregate_tables", smk)
    assert (
        "ERROR rule=aggregate_accuracy sample=- ValueError: "
        in (tmp_path / "aggregate_accuracy.log").read_text()
    )

from pathlib import Path

import pandas as pd
import pytest
from clinvar_summary import summarise
from smk_stub import DATA, make_smk, run_as_rule_script

HEADER = "chrom\tpos\tref\talt\tgt\tclinvar_id\tclnsig\tclnrevstat\tgeneinfo\n"
COLUMNS = ["sample", "caller", "clnsig", "calls"]


def _table(tmp_path: Path, sample: str, caller: str, sigs: list[str]) -> str:
    # summarise() reads the sample from the directory and the caller from the file name.
    path = tmp_path / sample / f"{caller}.clinvar.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        f"chr17\t{100 + i}\tA\tG\t0/1\t{i}\t{s}\tcriteria\tBRCA1:672\n" for i, s in enumerate(sigs)
    ]
    path.write_text(HEADER + "".join(rows))
    return str(path)


def _zero_row_table(tmp_path: Path, sample: str, caller: str) -> str:
    path = tmp_path / sample / f"{caller}.clinvar.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((DATA / "clinvar_zero_rows.tsv").read_bytes())
    return str(path)


def test_no_tables_gives_an_empty_summary_with_columns() -> None:
    out = summarise([])
    assert out.empty
    assert list(out.columns) == COLUMNS


def test_zero_row_table_gives_an_empty_summary_with_columns(tmp_path: Path) -> None:
    out = summarise([_zero_row_table(tmp_path, "HG002", "bcftools")])
    assert out.empty
    assert list(out.columns) == COLUMNS


def test_zero_row_tables_for_every_sample_and_caller(tmp_path: Path) -> None:
    paths = [_zero_row_table(tmp_path, s, c) for s in ("HG002", "HG003") for c in ("a", "b")]
    assert summarise(paths).empty


def test_zero_row_table_beside_a_populated_one(tmp_path: Path) -> None:
    out = summarise(
        [
            _zero_row_table(tmp_path, "HG002", "freebayes"),
            _table(tmp_path, "HG002", "bcftools", ["Pathogenic"]),
        ]
    )
    assert out.to_dict("records") == [
        {"sample": "HG002", "caller": "bcftools", "clnsig": "Pathogenic", "calls": 1}
    ]


def test_counts_sorted_by_sample_caller_then_descending_calls(tmp_path: Path) -> None:
    paths = [
        _table(tmp_path, "HG003", "bcftools", ["Benign"]),
        _table(tmp_path, "HG002", "freebayes", ["Benign", "Pathogenic", "Pathogenic"]),
        _table(tmp_path, "HG002", "bcftools", ["Uncertain_significance"]),
    ]
    out = summarise(paths)
    assert out[["sample", "caller", "clnsig", "calls"]].values.tolist() == [
        ["HG002", "bcftools", "Uncertain_significance", 1],
        ["HG002", "freebayes", "Pathogenic", 2],
        ["HG002", "freebayes", "Benign", 1],
        ["HG003", "bcftools", "Benign", 1],
    ]


def test_caller_name_stops_at_the_first_dot(tmp_path: Path) -> None:
    out = summarise([_table(tmp_path, "HG002", "bcftools", ["Benign"])])
    assert out["caller"].tolist() == ["bcftools"]


def test_empty_file_error_names_the_file(tmp_path: Path) -> None:
    path = tmp_path / "HG002" / "bcftools.clinvar.tsv"
    path.parent.mkdir()
    path.write_text("")
    with pytest.raises(ValueError, match=r"bcftools\.clinvar\.tsv: empty file"):
        summarise([str(path)])


@pytest.mark.parametrize("n_tables", [0, 1])
def test_rule_script_writes_a_header_for_empty_input(tmp_path: Path, n_tables: int) -> None:
    inputs = [_zero_row_table(tmp_path, "HG002", "bcftools")] if n_tables else []
    smk = make_smk(tmp_path, "clinvar_summary", input=inputs, output=[str(tmp_path / "out.tsv")])
    run_as_rule_script("clinvar_summary", smk)
    assert (tmp_path / "out.tsv").read_text() == "\t".join(COLUMNS) + "\n"
    assert "wrote 0 rows covering 0 calls" in (tmp_path / "clinvar_summary.log").read_text()


def test_rule_script_writes_counts(tmp_path: Path) -> None:
    smk = make_smk(
        tmp_path,
        "clinvar_summary",
        input=[_table(tmp_path, "HG002", "bcftools", ["Benign", "Benign"])],
        output=[str(tmp_path / "out.tsv")],
    )
    run_as_rule_script("clinvar_summary", smk)
    out = pd.read_csv(tmp_path / "out.tsv", sep="\t")
    assert out["calls"].tolist() == [2]
    assert "wrote 1 rows covering 2 calls" in (tmp_path / "clinvar_summary.log").read_text()

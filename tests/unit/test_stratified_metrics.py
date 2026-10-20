import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from smk_stub import DATA, Wildcards, make_smk, run_as_rule_script
from stratified_metrics import Counts, count_records, fmt

ROOT = Path(__file__).resolve().parents[2]
BCFTOOLS = shutil.which("bcftools")
BGZIP = shutil.which("bgzip")
TABIX = shutil.which("tabix")
needs_htslib = pytest.mark.skipif(
    not (BCFTOOLS and BGZIP and TABIX), reason="bcftools, bgzip and tabix are not on PATH"
)


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
    assert c.recall == 0 and c.precision == 0 and c.f1 == 0.0


@pytest.mark.parametrize(
    ("counts", "recall", "precision", "f1"),
    [
        pytest.param((0, 0, 0, 0), None, None, None, id="nothing-at-all"),
        pytest.param((10, 0, 10, 0), 1.0, 1.0, 1.0, id="perfect"),
        pytest.param((0, 4, 0, 0), 0.0, None, None, id="only-misses-has-no-precision"),
        pytest.param((0, 0, 0, 4), None, 0.0, None, id="only-false-positives-has-no-recall"),
        pytest.param((5, 0, 0, 0), 1.0, None, None, id="truth-side-only"),
        pytest.param((0, 0, 5, 0), None, 1.0, None, id="call-side-only"),
        pytest.param((1, 3, 1, 1), 0.25, 0.5, 1 / 3, id="unequal-sides"),
        pytest.param((3, 0, 2, 0), 1.0, 1.0, 1.0, id="truth-and-call-counts-may-differ"),
    ],
)
def test_counts_edge_cases(
    counts: tuple[int, int, int, int],
    recall: float | None,
    precision: float | None,
    f1: float | None,
) -> None:
    c = Counts(*counts)
    assert c.recall == pytest.approx(recall)
    assert c.precision == pytest.approx(precision)
    assert c.f1 == pytest.approx(f1)


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (None, "NA"),
        (0.0, "0.0000"),
        (1.0, "1.0000"),
        (0.12341, "0.1234"),
        (0.987654, "0.9877"),
        (2 / 3, "0.6667"),
    ],
)
def test_fmt(value: float | None, text: str) -> None:
    assert fmt(value) == text


def _index(tmp_path: Path, source: Path) -> str:
    assert BGZIP and TABIX
    target = tmp_path / source.name
    target.write_bytes(source.read_bytes())
    subprocess.run([BGZIP, "-f", str(target)], check=True)
    subprocess.run([TABIX, "-f", "-p", "vcf", f"{target}.gz"], check=True)
    return f"{target}.gz"


def _bed(tmp_path: Path, text: str, name: str = "stratum.bed") -> str:
    path = tmp_path / name
    path.write_bytes(text.encode())
    return str(path)


@needs_htslib
@pytest.mark.parametrize(
    ("fixture", "vtype", "bed", "expected"),
    [
        pytest.param("header_only.vcf", "snps", None, 0, id="header-only-snps"),
        pytest.param("header_only.vcf", "indels", None, 0, id="header-only-indels"),
        pytest.param("multiallelic.vcf", "snps", None, 3, id="multiallelic-snps"),
        pytest.param("multiallelic.vcf", "indels", None, 2, id="multiallelic-counts-in-both-types"),
        pytest.param("missing_info.vcf", "snps", None, 2, id="missing-info-snps"),
        pytest.param("missing_info.vcf", "indels", None, 1, id="missing-info-indels"),
        pytest.param(
            "multiallelic.vcf", "snps", "chr17\t0\t150\n", 1, id="bed-keeps-record-inside"
        ),
        pytest.param(
            "multiallelic.vcf", "indels", "chr17\t0\t150\n", 0, id="bed-drops-record-outside"
        ),
        pytest.param(
            "multiallelic.vcf", "snps", "chr17\t99\t100\n", 1, id="bed-is-zero-based-start"
        ),
        pytest.param(
            "multiallelic.vcf", "snps", "chr17\t100\t101\n", 0, id="bed-excludes-previous-base"
        ),
        pytest.param("multiallelic.vcf", "snps", "chr17\t99\t100\r\n", 1, id="bed-with-crlf"),
        pytest.param("multiallelic.vcf", "snps", "chr9\t0\t1000\n", 0, id="bed-on-another-contig"),
        pytest.param("multiallelic.vcf", "snps", "", 0, id="empty-bed-is-zero-not-an-error"),
    ],
)
def test_count_records(
    tmp_path: Path, fixture: str, vtype: str, bed: str | None, expected: int
) -> None:
    vcf = _index(tmp_path, DATA / fixture)
    assert count_records(vcf, vtype, None if bed is None else _bed(tmp_path, bed)) == expected


@needs_htslib
def test_count_records_names_the_file_when_bcftools_rejects_a_record(tmp_path: Path) -> None:
    vcf = _index(tmp_path, DATA / "malformed_columns.vcf")
    with pytest.raises(ValueError, match=r"malformed_columns\.vcf\.gz: bcftools view exited"):
        count_records(vcf, "snps", None)


@needs_htslib
def test_count_records_names_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"absent\.vcf\.gz"):
        count_records(str(tmp_path / "absent.vcf.gz"), "snps", None)


def test_empty_bed_short_circuits_before_calling_bcftools(tmp_path: Path) -> None:
    # No bcftools needed: a zero-byte stratum is answered without running anything.
    assert count_records(str(tmp_path / "never_read.vcf.gz"), "snps", _bed(tmp_path, "")) == 0


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


@needs_htslib
def test_rule_script_writes_one_row_per_stratum_and_type(tmp_path: Path) -> None:
    tp_base = _index(tmp_path, DATA / "multiallelic.vcf")
    fn = _index(tmp_path, DATA / "missing_info.vcf")
    empty = _index(tmp_path, DATA / "header_only.vcf")
    inside = _bed(tmp_path, "chr17\t0\t150\n", "inside.bed")
    nothing = _bed(tmp_path, "", "nothing.bed")
    smk = make_smk(
        tmp_path,
        "stratified_metrics",
        wildcards=Wildcards(sample="HG002", caller="bcftools"),
        input=SimpleNamespace(
            tp_base=tp_base, fn=fn, tp=tp_base, fp=empty, strata=[inside, nothing]
        ),
        params=SimpleNamespace(strata=["low_complexity", "unreachable"]),
        output=[str(tmp_path / "metrics.tsv")],
    )
    run_as_rule_script("stratified_metrics", smk)
    rows = [line.split("\t") for line in (tmp_path / "metrics.tsv").read_text().splitlines()]
    assert rows[0][:4] == ["sample", "caller", "stratum", "type"]
    by_key = {(r[2], r[3]): r[4:] for r in rows[1:]}
    assert len(rows) == 1 + 3 * 2
    # tp_base 3 SNV, fn 2 SNV, tp 3 SNV, fp 0: recall 3/5, precision 1, f1 0.75
    assert by_key[("all", "SNV")] == ["3", "2", "3", "0", "0.6000", "1.0000", "0.7500"]
    assert by_key[("all", "INDEL")][:4] == ["2", "1", "2", "0"]
    assert by_key[("low_complexity", "SNV")][:4] == ["1", "1", "1", "0"]
    # An empty stratum keeps its rows, with zero counts and NA metrics.
    assert by_key[("unreachable", "SNV")] == ["0", "0", "0", "0", "NA", "NA", "NA"]
    assert "wrote 6 rows" in (tmp_path / "stratified_metrics.log").read_text()


@needs_htslib
def test_rule_script_logs_the_file_that_bcftools_rejected(tmp_path: Path) -> None:
    bad = _index(tmp_path, DATA / "malformed_columns.vcf")
    ok = _index(tmp_path, DATA / "header_only.vcf")
    smk = make_smk(
        tmp_path,
        "stratified_metrics",
        wildcards=Wildcards(sample="HG002", caller="bcftools"),
        input=SimpleNamespace(tp_base=bad, fn=ok, tp=ok, fp=ok, strata=[]),
        params=SimpleNamespace(strata=[]),
        output=[str(tmp_path / "metrics.tsv")],
    )
    with pytest.raises(ValueError, match="malformed_columns"):
        run_as_rule_script("stratified_metrics", smk)
    log = (tmp_path / "stratified_metrics.log").read_text()
    assert "ERROR rule=stratified_metrics sample=HG002 ValueError: " in log
    assert "malformed_columns.vcf.gz" in log


def test_rule_declares_only_inputs_the_script_reads() -> None:
    # The vcfeval outputs are already limited to the confident regions, so the
    # rule needs no BED of its own; an input the script never reads only
    # suggests a filter that is not applied.
    rule = (ROOT / "workflow" / "rules" / "evaluate.smk").read_text()
    found = re.search(r"^rule stratified_metrics:\n(.*?)^    output:", rule, re.M | re.S)
    assert found is not None
    names = re.findall(r"^        (\w+)=", found.group(1), re.M)
    script = (ROOT / "workflow" / "scripts" / "stratified_metrics.py").read_text()
    assert names == ["tp", "tp_base", "fp", "fn", "strata"]
    # \b so that smk.input.tp_base does not count as a read of tp.
    assert [n for n in names if not re.search(rf"smk\.input\.{n}\b", script)] == []

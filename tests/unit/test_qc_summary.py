import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from qc_summary import fastp_metrics, mosdepth_mean, samtools_sn
from smk_stub import DATA, Wildcards, make_smk, run_as_rule_script


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_bytes(text.encode())
    return str(path)


def _fastp(before: int = 100, after: int = 98, q30: float = 0.912345, **extra: Any) -> str:
    return json.dumps(
        {
            "summary": {
                "before_filtering": {"total_reads": before},
                "after_filtering": {"total_reads": after, "q30_rate": q30},
            },
            **extra,
        }
    )


def test_fastp_metrics(tmp_path: Path) -> None:
    p = tmp_path / "f.json"
    p.write_text(
        json.dumps(
            {
                "summary": {
                    "before_filtering": {"total_reads": 100},
                    "after_filtering": {"total_reads": 98, "q30_rate": 0.912345},
                },
                "duplication": {"rate": 0.05},
            }
        )
    )
    m = fastp_metrics(str(p))
    assert m["reads_raw"] == 100 and m["reads_after_fastp"] == 98
    assert m["q30_rate_after"] == 0.9123


def test_fastp_fixture() -> None:
    assert fastp_metrics(str(DATA / "fastp.json")) == {
        "reads_raw": 10,
        "reads_after_fastp": 8,
        "q30_rate_after": 0.9224,
        "duplication_rate_fastp": 0.0521,
    }


@pytest.mark.parametrize(
    ("text", "dup"),
    [
        pytest.param(_fastp(), None, id="no-duplication-section"),
        pytest.param(_fastp(duplication={}), None, id="duplication-without-rate"),
        pytest.param(_fastp(duplication={"rate": 0.123456}), 0.1235, id="rate-rounded"),
        pytest.param(_fastp(0, 0, 0), None, id="no-reads-at-all"),
    ],
)
def test_fastp_metrics_missing_duplication_is_nan(
    tmp_path: Path, text: str, dup: float | None
) -> None:
    m = fastp_metrics(_write(tmp_path, "f.json", text))
    if dup is None:
        assert math.isnan(m["duplication_rate_fastp"])
    else:
        assert m["duplication_rate_fastp"] == dup


@pytest.mark.parametrize(
    ("text", "message"),
    [
        pytest.param("", r"f\.json:1: invalid JSON", id="empty-file"),
        pytest.param("{", r"f\.json:1: invalid JSON", id="truncated"),
        pytest.param('{\n  "summary": }', r"f\.json:2: invalid JSON", id="error-on-second-line"),
        pytest.param("{}", r"f\.json: fastp report has no 'summary' entry", id="no-summary"),
        pytest.param(
            '{"summary": {"before_filtering": {}, "after_filtering": {}}}',
            r"f\.json: fastp report has no 'total_reads' entry",
            id="no-counts",
        ),
    ],
)
def test_fastp_metrics_errors_name_the_file(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        fastp_metrics(_write(tmp_path, "f.json", text))


# Every SN key samtools_sn reads, in the order samtools stats writes them.
FULL_SN = (
    "SN\treads mapped:\t1000\n"
    "SN\treads properly paired:\t900\n"
    "SN\treads duplicated:\t20\n"
    "SN\terror rate:\t1.5e-03\t# mismatches\n"
    "SN\tinsert size average:\t312.5\n"
)
FULL_VALUES = {
    "reads_mapped": 1000.0,
    "reads_duplicated": 20.0,
    "error_rate": 0.0015,
    "insert_size_mean": 312.5,
    "reads_properly_paired": 900.0,
}


def test_samtools_sn_picks_named_fields(tmp_path: Path) -> None:
    p = tmp_path / "s.txt"
    p.write_text("# samtools stats\n" + FULL_SN + "FFQ\t1\n")
    assert samtools_sn(str(p)) == FULL_VALUES


def test_samtools_sn_rejects_a_file_cut_short(tmp_path: Path) -> None:
    # Only the first SN lines survived, as after a disk-full write.
    text = "# samtools stats\n" + "".join(FULL_SN.splitlines(keepends=True)[:2])
    with pytest.raises(
        ValueError, match=r"s\.txt: samtools stats summary has no 'reads duplicated:'"
    ):
        samtools_sn(_write(tmp_path, "s.txt", text))


def test_samtools_sn_rejects_a_file_with_no_summary(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"has no 'reads mapped:', 'reads duplicated:'"):
        samtools_sn(_write(tmp_path, "s.txt", "# only comments\nFFQ\t1\n"))


def test_samtools_sn_rejects_a_file_cut_inside_a_value(tmp_path: Path) -> None:
    # 'insert size average:\t312.5' cut to '31' would otherwise read as 31.0.
    text = FULL_SN.replace("312.5\n", "31")
    with pytest.raises(ValueError, match=r"s\.txt:5: file ends inside an SN line"):
        samtools_sn(_write(tmp_path, "s.txt", text))


@pytest.mark.parametrize("text", [pytest.param("", id="empty"), pytest.param("\n", id="blank")])
def test_samtools_sn_rejects_an_empty_file(tmp_path: Path, text: str) -> None:
    # samtools stats writes its summary even for a BAM with no reads, so an
    # empty stats file was cut short before anything reached the disk.
    with pytest.raises(ValueError, match=r"s\.txt: empty file"):
        samtools_sn(_write(tmp_path, "s.txt", text))


def test_samtools_stats_fixture() -> None:
    assert samtools_sn(str(DATA / "samtools_stats.txt")) == {
        "reads_mapped": 9.0,
        "reads_properly_paired": 8.0,
        "reads_duplicated": 2.0,
        "error_rate": 0.0015,
        "insert_size_mean": 312.5,
    }


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(FULL_SN.replace("\n", "\r\n"), FULL_VALUES, id="crlf"),
        pytest.param(
            FULL_SN + "SN\tsome other field:\t5\n", FULL_VALUES, id="unlisted-key-ignored"
        ),
        pytest.param(
            FULL_SN.replace("reads mapped:\t1000", "reads mapped:\t0"),
            {**FULL_VALUES, "reads_mapped": 0.0},
            id="zero",
        ),
        pytest.param(
            FULL_SN + "SN\treads mapped:\t2\n",
            {**FULL_VALUES, "reads_mapped": 2.0},
            id="last-value-wins",
        ),
        pytest.param(FULL_SN + "FFQ\t1", FULL_VALUES, id="no-trailing-newline"),
        pytest.param(FULL_SN + "sn\treads mapped:\t10\n", FULL_VALUES, id="lower-case-tag-ignored"),
    ],
)
def test_samtools_sn_edge_cases(tmp_path: Path, text: str, expected: dict[str, float]) -> None:
    assert samtools_sn(_write(tmp_path, "s.txt", text)) == expected


@pytest.mark.parametrize(
    ("text", "message"),
    [
        pytest.param(
            "SN\treads mapped:\n",
            r"s\.txt:1: expected SN, key and value columns, got 2",
            id="missing-value",
        ),
        pytest.param(
            "SN\treads mapped:\tNA\n",
            r"s\.txt:1: 'reads mapped:' is not numeric: 'NA'",
            id="na-value",
        ),
        pytest.param(
            "SN\terror rate:\tx\n", r"s\.txt:1: 'error rate:' is not numeric: 'x'", id="text-value"
        ),
    ],
)
def test_samtools_sn_errors_name_the_file_and_line(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        samtools_sn(_write(tmp_path, "s.txt", text))


def test_mosdepth_prefers_region_total(tmp_path: Path) -> None:
    p = tmp_path / "m.txt"
    p.write_text(
        "chrom\tlength\tbases\tmean\tmin\tmax\n"
        "chr17\t100\t3000\t30.0\t0\t60\n"
        "total\t100\t3000\t30.0\t0\t60\n"
        "total_region\t50\t1600\t32.0\t0\t60\n"
    )
    assert mosdepth_mean(str(p)) == {"mean_depth_regions": 32.0}


@pytest.mark.parametrize(
    ("fixture", "mean"),
    [
        ("mosdepth_with_total_region.summary.txt", 32.5),
        ("mosdepth_without_total_region.summary.txt", 0.02),
    ],
)
def test_mosdepth_fixtures(fixture: str, mean: float) -> None:
    assert mosdepth_mean(str(DATA / fixture)) == {"mean_depth_regions": mean}


HDR = "chrom\tlength\tbases\tmean\tmin\tmax\n"


@pytest.mark.parametrize(
    ("text", "mean"),
    [
        pytest.param(HDR + "total\t100\t1\t12.3456\t0\t6\n", 12.35, id="rounds-to-two-decimals"),
        pytest.param(HDR + "total\t100\t1\t0\t0\t0\n", 0.0, id="zero-depth"),
        pytest.param(HDR.replace("\n", "\r\n") + "total\t100\t1\t7.0\t0\t6\r\n", 7.0, id="crlf"),
        pytest.param(
            HDR + "total_region\t1\t1\t5.5\t0\t6\ntotal\t9\t9\t1.0\t0\t6\n",
            5.5,
            id="row-order-does-not-matter",
        ),
    ],
)
def test_mosdepth_edge_cases(tmp_path: Path, text: str, mean: float) -> None:
    assert mosdepth_mean(_write(tmp_path, "m.txt", text)) == {"mean_depth_regions": mean}


def test_mosdepth_na_mean_stays_na(tmp_path: Path) -> None:
    out = mosdepth_mean(_write(tmp_path, "m.txt", HDR + "total\t100\t1\tNA\t0\t6\n"))
    assert math.isnan(out["mean_depth_regions"])


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(HDR, id="header-only"),
        pytest.param(HDR + "chr17\t100\t3000\t30.0\t0\t60\n", id="per-contig-rows-only"),
    ],
)
def test_mosdepth_without_any_total_row_names_the_file(tmp_path: Path, text: str) -> None:
    with pytest.raises(ValueError, match=r"m\.txt: no total_region or total row"):
        mosdepth_mean(_write(tmp_path, "m.txt", text))


def test_mosdepth_empty_file_names_the_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"m\.txt: empty file"):
        mosdepth_mean(_write(tmp_path, "m.txt", ""))


def _smk(
    tmp_path: Path, samples: list[str], fastp: list[str], stats: list[str], md: list[str]
) -> Any:
    return make_smk(
        tmp_path,
        "qc_summary",
        params=SimpleNamespace(samples=samples),
        input=SimpleNamespace(fastp=fastp, stats=stats, mosdepth=md),
        output=[str(tmp_path / "qc.tsv")],
        wildcards=Wildcards(),
    )


def test_rule_script_writes_one_row_per_sample(tmp_path: Path) -> None:
    f, s = str(DATA / "fastp.json"), str(DATA / "samtools_stats.txt")
    m1 = str(DATA / "mosdepth_with_total_region.summary.txt")
    m2 = str(DATA / "mosdepth_without_total_region.summary.txt")
    run_as_rule_script("qc_summary", _smk(tmp_path, ["HG002", "HG003"], [f, f], [s, s], [m1, m2]))
    out = pd.read_csv(tmp_path / "qc.tsv", sep="\t")
    assert out["sample"].tolist() == ["HG002", "HG003"]
    assert out["mean_depth_regions"].tolist() == [32.5, 0.02]
    assert out["reads_raw"].tolist() == [10, 10]
    assert "wrote 2 samples" in (tmp_path / "qc_summary.log").read_text()


def test_rule_script_rejects_mismatched_input_counts(tmp_path: Path) -> None:
    f, s, m = (
        str(DATA / n)
        for n in ("fastp.json", "samtools_stats.txt", "mosdepth_with_total_region.summary.txt")
    )
    with pytest.raises(ValueError):
        run_as_rule_script("qc_summary", _smk(tmp_path, ["HG002", "HG003"], [f], [s], [m]))


def test_rule_script_logs_the_file_that_failed(tmp_path: Path) -> None:
    bad = _write(tmp_path, "bad.json", "{")
    s, m = str(DATA / "samtools_stats.txt"), str(DATA / "mosdepth_with_total_region.summary.txt")
    with pytest.raises(ValueError, match=r"bad\.json:1"):
        run_as_rule_script("qc_summary", _smk(tmp_path, ["HG002"], [bad], [s], [m]))
    log = (tmp_path / "qc_summary.log").read_text()
    assert "ERROR rule=qc_summary sample=- ValueError: " in log and "bad.json:1" in log

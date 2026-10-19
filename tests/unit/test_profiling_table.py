import math
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from profiling_table import KEEP, collect, per_rule_summary
from smk_stub import DATA, make_smk, run_as_rule_script

HEADER = "s\th:m:s\tmax_rss\tmax_vms\tmax_uss\tmax_pss\tio_in\tio_out\tmean_load\tcpu_time\n"


def _bench(path: Path, s: float, rss: float, cpu: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + f"{s}\t0:00:01\t{rss}\t1\t1\t0\t-\t-\t90\t{cpu}\n")


def _na_bench(path: Path, name: str = "HG002.tsv") -> None:
    target = path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((DATA / "benchmark_with_na.tsv").read_bytes())


def test_collect_reads_nested_and_flat_benchmarks(tmp_path: Path) -> None:
    _bench(tmp_path / "bwa_index.tsv", 100.0, 5000.0, 99.0)
    _bench(tmp_path / "call_bcftools" / "HG002.0001.tsv", 10.0, 50.0, 9.0)
    _bench(tmp_path / "call_bcftools" / "HG002.0002.tsv", 20.0, 70.0, 19.0)
    df = collect(tmp_path)
    assert set(df["rule"]) == {"bwa_index", "call_bcftools"}
    assert list(df.loc[df["rule"] == "call_bcftools", "sample"]) == ["HG002", "HG002"]
    summary = per_rule_summary(df).set_index("rule")
    assert summary.loc["call_bcftools", "jobs"] == 2
    assert summary.loc["call_bcftools", "wall_s_total"] == 30.0
    assert summary.loc["call_bcftools", "max_rss_mb_peak"] == 70.0


def test_collect_on_an_empty_directory_has_the_full_column_set(tmp_path: Path) -> None:
    df = collect(tmp_path)
    assert df.empty
    assert list(df.columns) == ["rule", "job", *KEEP, "sample"]
    assert per_rule_summary(df).empty


def test_collect_header_only_benchmark_adds_no_rows(tmp_path: Path) -> None:
    (tmp_path / "fastp").mkdir()
    (tmp_path / "fastp" / "HG002.tsv").write_text(HEADER)
    assert collect(tmp_path).empty


def test_collect_ignores_files_that_are_not_tsv(tmp_path: Path) -> None:
    (tmp_path / "fastp").mkdir()
    (tmp_path / "fastp" / "notes.txt").write_text("not a benchmark")
    assert collect(tmp_path).empty


@pytest.mark.parametrize(
    ("relative", "rule", "job", "sample"),
    [
        pytest.param("bwa_index.tsv", "bwa_index", "", "", id="flat-file"),
        pytest.param("fastp/HG002.tsv", "fastp", "HG002", "HG002", id="one-wildcard"),
        pytest.param("vcfeval/HG002.bcftools.tsv", "vcfeval", "HG002.bcftools", "HG002", id="two"),
        pytest.param("call/HG002.0001.tsv", "call", "HG002.0001", "HG002", id="chunk-wildcard"),
        pytest.param("call/HG002.tsv.tsv", "call", "HG002.tsv", "HG002", id="dotted-name"),
    ],
)
def test_collect_names_rule_job_and_sample(
    tmp_path: Path, relative: str, rule: str, job: str, sample: str
) -> None:
    _bench(tmp_path / relative, 1.0, 2.0, 3.0)
    row = collect(tmp_path).iloc[0]
    assert (row["rule"], row["job"], row["sample"]) == (rule, job, sample)


def test_na_values_are_missing_not_zero(tmp_path: Path) -> None:
    _na_bench(tmp_path / "fastp")
    df = collect(tmp_path)
    assert df.loc[0, "s"] == pytest.approx(12.3456)
    assert df.loc[0, ["max_rss", "cpu_time", "mean_load"]].isna().all()


def test_summary_reports_na_when_no_job_measured_cpu_or_memory(tmp_path: Path) -> None:
    # macOS without the psutil shim writes NA for every resource column; the summary
    # must say so rather than show 0.0 s of CPU for a job that ran.
    _na_bench(tmp_path / "fastp", "HG002.tsv")
    _na_bench(tmp_path / "fastp", "HG003.tsv")
    row = per_rule_summary(collect(tmp_path)).iloc[0]
    assert row["jobs"] == 2
    assert row["wall_s_total"] == pytest.approx(24.7)
    assert math.isnan(row["cpu_s_total"])
    assert math.isnan(row["max_rss_mb_peak"])


def test_summary_sums_over_the_jobs_that_did_report(tmp_path: Path) -> None:
    _na_bench(tmp_path / "fastp", "HG002.tsv")
    _bench(tmp_path / "fastp" / "HG003.tsv", 5.0, 40.0, 4.5)
    row = per_rule_summary(collect(tmp_path)).iloc[0]
    assert row["cpu_s_total"] == pytest.approx(4.5)
    assert row["max_rss_mb_peak"] == pytest.approx(40.0)
    assert row["jobs"] == 2


def test_summary_rounds_to_one_decimal() -> None:
    df = pd.DataFrame(
        {"rule": ["a", "a"], "s": [1.04, 2.04], "cpu_time": [0.14, 0.14], "max_rss": [10.26, 3.0]}
    )
    row = per_rule_summary(df).iloc[0]
    assert (row["wall_s_total"], row["wall_s_max"]) == (3.1, 2.0)
    assert (row["cpu_s_total"], row["max_rss_mb_peak"]) == (0.3, 10.3)


def test_empty_benchmark_file_error_names_the_file(tmp_path: Path) -> None:
    (tmp_path / "fastp").mkdir()
    (tmp_path / "fastp" / "HG002.tsv").write_text("")
    with pytest.raises(ValueError, match=r"HG002\.tsv: empty file"):
        collect(tmp_path)


def test_rule_script_writes_both_tables_and_logs_counts(tmp_path: Path) -> None:
    bench = tmp_path / "benchmarks"
    _bench(bench / "call_bcftools" / "HG002.0001.tsv", 10.0, 50.0, 9.0)
    _bench(bench / "bwa_index.tsv", 100.0, 5000.0, 99.0)
    smk = make_smk(
        tmp_path,
        "profiling_table",
        params=SimpleNamespace(benchmark_dir=str(bench)),
        output=SimpleNamespace(table=str(tmp_path / "t.tsv"), by_rule=str(tmp_path / "r.tsv")),
    )
    run_as_rule_script("profiling_table", smk)
    assert len(pd.read_csv(tmp_path / "t.tsv", sep="\t")) == 2
    assert pd.read_csv(tmp_path / "r.tsv", sep="\t")["rule"].tolist() == [
        "bwa_index",
        "call_bcftools",
    ]
    log = (tmp_path / "profiling_table.log").read_text()
    assert "read 2 benchmark records" in log and "wrote 2 records" in log and "2 rules" in log


def test_rule_script_with_no_benchmarks_writes_empty_tables(tmp_path: Path) -> None:
    (tmp_path / "benchmarks").mkdir()
    smk = make_smk(
        tmp_path,
        "profiling_table",
        params=SimpleNamespace(benchmark_dir=str(tmp_path / "benchmarks")),
        output=SimpleNamespace(table=str(tmp_path / "t.tsv"), by_rule=str(tmp_path / "r.tsv")),
    )
    run_as_rule_script("profiling_table", smk)
    assert (tmp_path / "t.tsv").read_text().splitlines()[0].startswith("rule\tjob\ts")
    assert (tmp_path / "r.tsv").read_text().splitlines() == [
        "rule\tjobs\twall_s_total\twall_s_max\tcpu_s_total\tmax_rss_mb_peak"
    ]

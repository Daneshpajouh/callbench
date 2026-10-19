from pathlib import Path

from profiling_table import collect, per_rule_summary

HEADER = "s\th:m:s\tmax_rss\tmax_vms\tmax_uss\tmax_pss\tio_in\tio_out\tmean_load\tcpu_time\n"


def _bench(path: Path, s: float, rss: float, cpu: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + f"{s}\t0:00:01\t{rss}\t1\t1\t0\t-\t-\t90\t{cpu}\n")


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

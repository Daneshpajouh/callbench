import json
from pathlib import Path

from qc_summary import fastp_metrics, mosdepth_mean, samtools_sn


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


def test_samtools_sn_picks_named_fields(tmp_path: Path) -> None:
    p = tmp_path / "s.txt"
    p.write_text("SN\treads mapped:\t1000\nSN\terror rate:\t1.5e-03\t# mismatches\nFFQ\t1\n")
    assert samtools_sn(str(p)) == {"reads_mapped": 1000.0, "error_rate": 0.0015}


def test_mosdepth_prefers_region_total(tmp_path: Path) -> None:
    p = tmp_path / "m.txt"
    p.write_text(
        "chrom\tlength\tbases\tmean\tmin\tmax\n"
        "chr17\t100\t3000\t30.0\t0\t60\n"
        "total\t100\t3000\t30.0\t0\t60\n"
        "total_region\t50\t1600\t32.0\t0\t60\n"
    )
    assert mosdepth_mean(str(p)) == {"mean_depth_regions": 32.0}

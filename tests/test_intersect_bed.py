import gzip
from pathlib import Path

from intersect_bed import intersect, merge, read_bed


def test_merge_joins_overlapping_and_touching() -> None:
    assert merge([("c", 5, 10), ("c", 0, 5), ("c", 8, 12), ("c", 20, 30)]) == [
        ("c", 0, 12),
        ("c", 20, 30),
    ]


def test_merge_drops_empty_intervals() -> None:
    assert merge([("c", 5, 5)]) == []


def test_intersect_clips_to_regions() -> None:
    a = [("chr17", 0, 100), ("chr17", 150, 300), ("chr13", 0, 50)]
    b = [("chr17", 50, 200)]
    assert intersect(a, b) == [("chr17", 50, 100), ("chr17", 150, 200)]


def test_intersect_handles_interval_starting_at_zero() -> None:
    assert intersect([("c", 0, 10)], [("c", 0, 5)]) == [("c", 0, 5)]


def test_read_bed_reads_gzip_and_skips_headers(tmp_path: Path) -> None:
    p = tmp_path / "x.bed.gz"
    with gzip.open(p, "wt") as fh:
        fh.write("#chrom\tstart\tend\ntrack name=x\nchr1\t1\t5\textra\n")
    assert read_bed(p) == [("chr1", 1, 5)]

from pathlib import Path

import pytest
from scatter_intervals import read_bed, split_intervals, write_chunks


def test_split_respects_chunk_size_and_covers_input() -> None:
    chunks = split_intervals([("chr17", 100, 1150)], 500)
    assert chunks == [("chr17", 100, 600), ("chr17", 600, 1100), ("chr17", 1100, 1150)]
    assert sum(e - s for _, s, e in chunks) == 1050


def test_split_keeps_intervals_on_their_own_contig() -> None:
    chunks = split_intervals([("chr13", 0, 10), ("chr17", 0, 10)], 100)
    assert [c for c, _, _ in chunks] == ["chr13", "chr17"]


def test_split_rejects_non_positive_size() -> None:
    with pytest.raises(ValueError):
        split_intervals([("chr1", 0, 10)], 0)


def test_write_chunks_names_are_zero_padded(tmp_path: Path) -> None:
    bed = tmp_path / "in.bed"
    bed.write_text("chr17\t0\t25\n")
    paths = write_chunks(split_intervals(read_bed(bed), 10), tmp_path / "out")
    assert [p.name for p in paths] == ["0001.bed", "0002.bed", "0003.bed"]
    assert paths[-1].read_text() == "chr17\t20\t25\n"

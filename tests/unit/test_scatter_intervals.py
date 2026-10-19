import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from scatter_intervals import Interval, read_bed, split_intervals, write_chunks
from smk_stub import DATA, SCRIPTS, make_smk, run_as_rule_script


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


@pytest.mark.parametrize(
    ("intervals", "size", "expected"),
    [
        pytest.param([], 100, [], id="empty-input"),
        pytest.param([("chr1", 0, 0)], 100, [], id="zero-length-at-origin"),
        pytest.param([("chr1", 50, 50)], 100, [], id="zero-length-inside-contig"),
        pytest.param([("chr1", 60, 50)], 100, [], id="reversed-interval-yields-nothing"),
        pytest.param([("chr1", 0, 1)], 100, [("chr1", 0, 1)], id="one-base-at-origin"),
        pytest.param([("chr1", 0, 10)], 1000, [("chr1", 0, 10)], id="chunk-larger-than-interval"),
        pytest.param([("chr1", 0, 10)], 10, [("chr1", 0, 10)], id="chunk-equals-interval"),
        pytest.param([("chr1", 0, 10)], 5, [("chr1", 0, 5), ("chr1", 5, 10)], id="exact-multiple"),
        pytest.param(
            [("chr1", 0, 11)],
            5,
            [("chr1", 0, 5), ("chr1", 5, 10), ("chr1", 10, 11)],
            id="one-base-remainder",
        ),
        pytest.param(
            [("chr1", 0, 3)],
            1,
            [("chr1", 0, 1), ("chr1", 1, 2), ("chr1", 2, 3)],
            id="chunk-of-one-base",
        ),
        pytest.param(
            [("chr1", 5, 10), ("chr1", 0, 5)],
            100,
            [("chr1", 5, 10), ("chr1", 0, 5)],
            id="input-order-kept-and-touching-intervals-not-merged",
        ),
        pytest.param(
            [("chr1", 0, 10), ("chr1", 0, 10)],
            100,
            [("chr1", 0, 10), ("chr1", 0, 10)],
            id="duplicates-kept",
        ),
        pytest.param(
            [("chr1", 0, 0), ("chr2", 0, 4)],
            2,
            [("chr2", 0, 2), ("chr2", 2, 4)],
            id="skip-empty-then-split",
        ),
    ],
)
def test_split_intervals_edge_cases(
    intervals: list[Interval], size: int, expected: list[Interval]
) -> None:
    assert split_intervals(intervals, size) == expected


@pytest.mark.parametrize("size", [0, -1, -500])
def test_split_rejects_bad_size_even_without_intervals(size: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        split_intervals([], size)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", [], id="empty-file"),
        pytest.param("\n\n   \n", [], id="blank-lines-only"),
        pytest.param("#header\ntrack name=x\nbrowser position chr1\n", [], id="headers-only"),
        pytest.param("chr1\t0\t10", [("chr1", 0, 10)], id="no-trailing-newline"),
        pytest.param("chr1\t0\t10\textra\tcols\n", [("chr1", 0, 10)], id="extra-columns-ignored"),
        pytest.param(
            "chr1\t0\t10\r\nchr1\t20\t30\r\n", [("chr1", 0, 10), ("chr1", 20, 30)], id="crlf"
        ),
        pytest.param("\nchr1\t0\t10\n\n", [("chr1", 0, 10)], id="blank-lines-between-records"),
        pytest.param("chr1\t0\t0\n", [("chr1", 0, 0)], id="zero-length-kept-by-reader"),
    ],
)
def test_read_bed_edge_cases(tmp_path: Path, text: str, expected: list[Interval]) -> None:
    bed = tmp_path / "x.bed"
    bed.write_bytes(text.encode())
    assert read_bed(bed) == expected


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("chr1\t5\n", id="two-columns"),
        pytest.param("chr1\n", id="one-column"),
        pytest.param("chr1\tfive\t10\n", id="non-numeric-start"),
        pytest.param("chr1\t5\t10.5\n", id="fractional-end"),
        pytest.param("chr1 0 10\n", id="space-separated"),
    ],
)
def test_read_bed_rejects_malformed_records(tmp_path: Path, text: str) -> None:
    bed = tmp_path / "bad.bed"
    bed.write_text(text)
    with pytest.raises(ValueError):
        read_bed(bed)


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("with_chr_prefix.bed", [("chr17", 0, 100), ("chr17", 150, 300), ("chr13", 10, 50)]),
        ("without_chr_prefix.bed", [("17", 0, 100), ("17", 150, 300), ("13", 10, 50)]),
        ("empty.bed", []),
        ("crlf.bed", [("chr17", 0, 100), ("chr17", 150, 300), ("chr13", 10, 50)]),
        ("regions.bed", [("chr17", 0, 100), ("chr17", 150, 300), ("chr13", 10, 50)]),
    ],
)
def test_read_bed_fixtures(fixture: str, expected: list[Interval]) -> None:
    assert read_bed(DATA / fixture) == expected


def test_write_chunks_with_no_chunks_creates_an_empty_directory(tmp_path: Path) -> None:
    # The checkpoint output is a directory; an empty target must still produce one.
    out = tmp_path / "scatter"
    assert write_chunks([], out) == []
    assert out.is_dir()
    assert list(out.iterdir()) == []


def test_write_chunks_accepts_an_existing_directory(tmp_path: Path) -> None:
    out = tmp_path / "scatter"
    out.mkdir()
    assert [p.name for p in write_chunks([("chr1", 0, 5)], out)] == ["0001.bed"]


def test_write_chunks_writes_one_tab_separated_record_per_file(tmp_path: Path) -> None:
    paths = write_chunks([("chr13", 0, 5), ("chr17", 7, 9)], tmp_path / "o")
    assert [p.read_text() for p in paths] == ["chr13\t0\t5\n", "chr17\t7\t9\n"]


def test_chunks_from_fixture_cover_the_regions_exactly(tmp_path: Path) -> None:
    regions = read_bed(DATA / "with_chr_prefix.bed")
    paths = write_chunks(split_intervals(regions, 64), tmp_path / "o")
    total = sum(e - s for p in paths for _, s, e in read_bed(p))
    assert total == sum(e - s for _, s, e in regions)
    assert max(e - s for p in paths for _, s, e in read_bed(p)) <= 64


def _smk(tmp_path: Path, regions: Path, chunk_size: object) -> SimpleNamespace:
    return make_smk(
        tmp_path,
        "scatter_intervals",
        input=SimpleNamespace(regions=str(regions)),
        params=SimpleNamespace(chunk_size=chunk_size),
        output=[str(tmp_path / "chunks")],
    )


@pytest.mark.parametrize("chunk_size", [100, "100"])
def test_rule_script_writes_chunks_and_log(tmp_path: Path, chunk_size: object) -> None:
    # Snakemake params can arrive as strings when they come from a config override.
    run_as_rule_script(
        "scatter_intervals", _smk(tmp_path, DATA / "with_chr_prefix.bed", chunk_size)
    )
    names = sorted(p.name for p in (tmp_path / "chunks").iterdir())
    assert names == ["0001.bed", "0002.bed", "0003.bed", "0004.bed"]
    log = (tmp_path / "scatter_intervals.log").read_text()
    assert "rule=scatter_intervals sample=- wrote 4 chunks of at most 100 bp" in log
    assert "read 3 intervals" in log


def test_rule_script_with_empty_regions_writes_zero_chunks(tmp_path: Path) -> None:
    run_as_rule_script("scatter_intervals", _smk(tmp_path, DATA / "empty.bed", 100))
    assert list((tmp_path / "chunks").iterdir()) == []
    assert "wrote 0 chunks of at most 100 bp" in (tmp_path / "scatter_intervals.log").read_text()


def test_command_line_entry_point(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "cli"
    argv = ["scatter_intervals.py", str(DATA / "with_chr_prefix.bed"), "150", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    runpy.run_path(str(SCRIPTS / "scatter_intervals.py"), run_name="__main__")
    assert sorted(p.name for p in out.iterdir()) == ["0001.bed", "0002.bed", "0003.bed"]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        pytest.param(
            "chr1\t5\n",
            "x.bed:1: expected at least 3 tab-separated columns, got 2",
            id="short-first-line",
        ),
        pytest.param(
            "chr1\t0\t10\n#c\nchr1 0 10\n",
            "x.bed:3: expected at least 3 tab-separated columns, got 1",
            id="space-separated-third-line",
        ),
        pytest.param(
            "chr1\tfive\t10\n",
            "x.bed:1: start and end must be integers, got 'five' and '10'",
            id="non-numeric",
        ),
    ],
)
def test_read_bed_errors_name_the_file_and_line(tmp_path: Path, text: str, message: str) -> None:
    bed = tmp_path / "x.bed"
    bed.write_text(text)
    with pytest.raises(ValueError) as info:
        read_bed(bed)
    assert message in str(info.value).replace(str(tmp_path) + "/", "")


def test_rule_script_logs_the_error_before_failing(tmp_path: Path) -> None:
    bad = tmp_path / "bad.bed"
    bad.write_text("chr1\t5\n")
    with pytest.raises(ValueError, match="expected at least 3"):
        run_as_rule_script("scatter_intervals", _smk(tmp_path, bad, 100))
    assert (
        "ERROR rule=scatter_intervals sample=- ValueError: "
        in (tmp_path / "scatter_intervals.log").read_text()
    )

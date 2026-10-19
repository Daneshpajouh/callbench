import gzip
import random
from pathlib import Path
from types import SimpleNamespace

import pytest
from intersect_bed import Interval, intersect, merge, read_bed, write_bed
from smk_stub import DATA, Files, make_smk, run_as_rule_script


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


@pytest.mark.parametrize(
    ("intervals", "expected"),
    [
        pytest.param([], [], id="empty"),
        pytest.param([("c", 0, 0)], [], id="zero-length-at-origin"),
        pytest.param([("c", 7, 3)], [], id="reversed-interval"),
        pytest.param([("c", 0, 1)], [("c", 0, 1)], id="one-base-at-origin"),
        pytest.param([("c", 0, 5), ("c", 5, 9)], [("c", 0, 9)], id="touching-at-zero-start"),
        pytest.param([("c", 0, 5), ("c", 6, 9)], [("c", 0, 5), ("c", 6, 9)], id="gap-of-one"),
        pytest.param([("c", 0, 100), ("c", 10, 20)], [("c", 0, 100)], id="nested"),
        pytest.param([("c", 3, 4), ("c", 1, 2), ("c", 2, 3)], [("c", 1, 4)], id="unsorted-chain"),
        pytest.param([("c", 0, 5), ("c", 0, 5)], [("c", 0, 5)], id="duplicates"),
        pytest.param(
            [("chr2", 0, 5), ("chr10", 0, 5), ("chr1", 0, 5)],
            [("chr1", 0, 5), ("chr10", 0, 5), ("chr2", 0, 5)],
            id="contigs-sorted-as-strings",
        ),
        pytest.param([("c", 5, 5), ("c", 0, 5)], [("c", 0, 5)], id="empty-interval-between"),
        pytest.param(
            [("c", 0, 0), ("c", 0, 0), ("c", 10, 10)], [], id="only-zero-length-intervals"
        ),
    ],
)
def test_merge_edge_cases(intervals: list[Interval], expected: list[Interval]) -> None:
    assert merge(intervals) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        pytest.param([], [("c", 0, 10)], [], id="empty-a"),
        pytest.param([("c", 0, 10)], [], [], id="empty-b"),
        pytest.param([], [], [], id="both-empty"),
        pytest.param([("c", 0, 10)], [("c", 10, 20)], [], id="touching-edges-do-not-overlap"),
        pytest.param([("c", 0, 10)], [("c", 9, 20)], [("c", 9, 10)], id="one-base-overlap"),
        pytest.param([("c", 0, 10)], [("c", 0, 0)], [], id="zero-length-b-ignored"),
        pytest.param([("c", 5, 5)], [("c", 0, 10)], [], id="zero-length-a-ignored"),
        pytest.param([("c", 0, 10)], [("d", 0, 10)], [], id="different-contigs"),
        pytest.param([("c", 4, 6)], [("c", 0, 10)], [("c", 4, 6)], id="a-inside-b"),
        pytest.param([("c", 0, 100)], [("c", 10, 20)], [("c", 10, 20)], id="b-inside-a"),
        pytest.param(
            [("c", 0, 100)],
            [("c", 60, 70), ("c", 10, 20), ("c", 15, 30)],
            [("c", 10, 30), ("c", 60, 70)],
            id="b-unsorted-and-overlapping",
        ),
        pytest.param(
            [("c", 0, 10), ("c", 5, 15)],
            [("c", 0, 15)],
            [("c", 0, 15)],
            id="a-overlapping-is-merged-first",
        ),
        pytest.param(
            [("chr1", 0, 10), ("chr2", 0, 10)],
            [("chr2", 5, 20)],
            [("chr2", 5, 10)],
            id="only-shared-contig-survives",
        ),
    ],
)
def test_intersect_edge_cases(
    a: list[Interval], b: list[Interval], expected: list[Interval]
) -> None:
    assert intersect(a, b) == expected


def test_intersect_with_chr_prefix_mismatch_is_empty() -> None:
    # Contig names are compared as strings, so "chr17" and "17" never meet. The
    # script does not guess a rename; the rule that calls it passes BEDs that
    # already use the reference naming.
    prefixed = read_bed(DATA / "with_chr_prefix.bed")
    bare = read_bed(DATA / "without_chr_prefix.bed")
    assert intersect(prefixed, bare) == []
    assert intersect(bare, bare) == merge(bare)


@pytest.mark.parametrize("seed", range(8))
def test_intersect_matches_a_base_by_base_reference(seed: int) -> None:
    rng = random.Random(seed)

    def draw() -> list[Interval]:
        out: list[Interval] = []
        for _ in range(rng.randint(0, 6)):
            start = rng.randint(0, 40)
            out.append((rng.choice(["c1", "c2"]), start, start + rng.randint(0, 12)))
        return out

    def bases(intervals: list[Interval]) -> set[tuple[str, int]]:
        return {(c, i) for c, s, e in intervals for i in range(s, e)}

    a, b = draw(), draw()
    assert bases(intersect(a, b)) == bases(a) & bases(b)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", [], id="empty-file"),
        pytest.param("\n  \n\t\n", [], id="blank-lines-only"),
        pytest.param("#h\ntrack name=x\nbrowser dense\n", [], id="headers-only"),
        pytest.param("chr1\t0\t10", [("chr1", 0, 10)], id="no-trailing-newline"),
        pytest.param(
            "chr1\t0\t10\r\nchr1\t20\t30\r\n", [("chr1", 0, 10), ("chr1", 20, 30)], id="crlf"
        ),
        pytest.param("chr1\t0\t10\tname\r\n", [("chr1", 0, 10)], id="crlf-with-name-column"),
        pytest.param("chr1\t0\t10\textra\t1\t+\n", [("chr1", 0, 10)], id="bed6"),
        pytest.param("chr1\t0\t0\n", [("chr1", 0, 0)], id="zero-length-kept-by-reader"),
    ],
)
def test_read_bed_edge_cases(tmp_path: Path, text: str, expected: list[Interval]) -> None:
    plain = tmp_path / "x.bed"
    plain.write_bytes(text.encode())
    gz = tmp_path / "x.bed.gz"
    gz.write_bytes(gzip.compress(text.encode()))
    assert read_bed(plain) == expected
    assert read_bed(gz) == expected


@pytest.mark.parametrize(
    ("text", "error"),
    [
        pytest.param("chr1\n", ValueError, id="one-column"),
        pytest.param("chr1\t5\n", ValueError, id="two-columns"),
        pytest.param("chr1 0 10\n", ValueError, id="space-separated"),
        pytest.param("chr1\tx\t10\n", ValueError, id="non-numeric-start"),
        pytest.param("chr1\t0\tNA\n", ValueError, id="na-end"),
    ],
)
def test_read_bed_fails_loudly_on_malformed_records(
    tmp_path: Path, text: str, error: type[Exception]
) -> None:
    bed = tmp_path / "bad.bed"
    bed.write_text(text)
    with pytest.raises(error):
        read_bed(bed)


def test_gzipped_and_plain_fixtures_agree() -> None:
    assert read_bed(DATA / "regions.bed.gz") == read_bed(DATA / "regions.bed")
    assert len(read_bed(DATA / "regions.bed")) == 3


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("empty.bed", []),
        ("crlf.bed", [("chr17", 0, 100), ("chr17", 150, 300), ("chr13", 10, 50)]),
        ("with_chr_prefix.bed", [("chr17", 0, 100), ("chr17", 150, 300), ("chr13", 10, 50)]),
        ("without_chr_prefix.bed", [("17", 0, 100), ("17", 150, 300), ("13", 10, 50)]),
    ],
)
def test_read_bed_fixtures(fixture: str, expected: list[Interval]) -> None:
    assert read_bed(DATA / fixture) == expected


def test_crlf_fixture_really_has_crlf_endings() -> None:
    assert b"\r\n" in (DATA / "crlf.bed").read_bytes()


@pytest.mark.parametrize(
    ("intervals", "count", "text"),
    [
        pytest.param([], 0, "", id="empty"),
        pytest.param([("c", 0, 5)], 1, "c\t0\t5\n", id="one-record"),
        pytest.param([("c", 0, 5), ("d", 7, 9)], 2, "c\t0\t5\nd\t7\t9\n", id="two-records"),
    ],
)
def test_write_bed(tmp_path: Path, intervals: list[Interval], count: int, text: str) -> None:
    out = tmp_path / "o.bed"
    assert write_bed(intervals, out) == count
    assert out.read_text() == text


def test_write_bed_accepts_a_generator(tmp_path: Path) -> None:
    out = tmp_path / "o.bed"
    assert write_bed(((c, 0, 1) for c in ("a", "b")), out) == 2


def _smk(tmp_path: Path, truth: Path, regions: Path) -> SimpleNamespace:
    return make_smk(
        tmp_path,
        "stratum_regions",
        input=Files(str(truth), regions=str(regions)),
        output=[str(tmp_path / "out.bed")],
    )


def test_rule_script_intersects_truth_with_regions(tmp_path: Path) -> None:
    regions = tmp_path / "regions.bed"
    regions.write_text("chr17\t50\t160\n")
    run_as_rule_script("intersect_bed", _smk(tmp_path, DATA / "regions.bed.gz", regions))
    assert (tmp_path / "out.bed").read_text() == "chr17\t50\t100\nchr17\t150\t160\n"
    assert "wrote 2 intervals, 60 bp" in (tmp_path / "stratum_regions.log").read_text()


def test_rule_script_with_empty_result_writes_an_empty_bed(tmp_path: Path) -> None:
    # An empty stratum is expected on small slices, and downstream steps rely on the
    # file existing.
    run_as_rule_script(
        "intersect_bed", _smk(tmp_path, DATA / "without_chr_prefix.bed", DATA / "regions.bed")
    )
    assert (tmp_path / "out.bed").read_text() == ""
    assert "wrote 0 intervals, 0 bp" in (tmp_path / "stratum_regions.log").read_text()


@pytest.mark.parametrize(
    ("text", "message"),
    [
        pytest.param(
            "chr1\t5\n",
            "x.bed:1: expected at least 3 tab-separated columns, got 2",
            id="short-first-line",
        ),
        pytest.param(
            "#h\nchr1 0 10\n",
            "x.bed:2: expected at least 3 tab-separated columns, got 1",
            id="space-separated",
        ),
        pytest.param(
            "chr1\t0\tNA\n",
            "x.bed:1: start and end must be integers, got '0' and 'NA'",
            id="na-end",
        ),
    ],
)
@pytest.mark.parametrize("suffix", ["", ".gz"])
def test_read_bed_errors_name_the_file_and_line(
    tmp_path: Path, text: str, message: str, suffix: str
) -> None:
    bed = tmp_path / f"x.bed{suffix}"
    bed.write_bytes(gzip.compress(text.encode()) if suffix else text.encode())
    with pytest.raises(ValueError) as info:
        read_bed(bed)
    assert message.replace("x.bed", f"x.bed{suffix}") in str(info.value).replace(
        str(tmp_path) + "/", ""
    )


def test_rule_script_logs_the_error_before_failing(tmp_path: Path) -> None:
    bad = tmp_path / "bad.bed"
    bad.write_text("chr1\t5\n")
    with pytest.raises(ValueError, match=r"bad\.bed:1"):
        run_as_rule_script("intersect_bed", _smk(tmp_path, bad, DATA / "regions.bed"))
    assert (
        "ERROR rule=stratum_regions sample=- ValueError: "
        in (tmp_path / "stratum_regions.log").read_text()
    )

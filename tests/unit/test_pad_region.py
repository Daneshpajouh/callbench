import subprocess
from pathlib import Path

import pytest
from smk_stub import SCRIPTS

AWK = SCRIPTS / "pad_region.awk"


def _pad(tmp_path: Path, bed: str, pad: int = 1000) -> subprocess.CompletedProcess[str]:
    fai = tmp_path / "genome.fa.fai"
    fai.write_text("chr17\t83257441\t7\t60\t61\nchr13\t114364328\t8\t60\t61\n")
    chunk = tmp_path / "0001.bed"
    chunk.write_text(bed)
    return subprocess.run(
        ["awk", "-v", f"pad={pad}", "-f", str(AWK), str(fai), str(chunk)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_chunk_is_padded_on_both_sides(tmp_path: Path) -> None:
    out = _pad(tmp_path, "chr17\t43000000\t43050000\n")
    assert out.returncode == 0
    assert out.stdout.strip() == "chr17:42999000-43051000"


def test_start_is_clamped_at_zero(tmp_path: Path) -> None:
    assert _pad(tmp_path, "chr13\t400\t5000\n").stdout.strip() == "chr13:0-6000"


def test_end_is_clamped_at_the_contig_length(tmp_path: Path) -> None:
    out = _pad(tmp_path, "chr17\t83257000\t83257441\n")
    assert out.stdout.strip() == "chr17:83256000-83257441"


def test_zero_padding_gives_the_chunk_itself(tmp_path: Path) -> None:
    assert _pad(tmp_path, "chr17\t10\t20\n", pad=0).stdout.strip() == "chr17:10-20"


def test_header_lines_are_skipped(tmp_path: Path) -> None:
    out = _pad(tmp_path, "track name=x\n# note\nchr17\t1000\t2000\n", pad=10)
    assert out.stdout.strip() == "chr17:990-2010"


@pytest.mark.parametrize(
    ("bed", "message"),
    [
        pytest.param("chrX\t1\t2\n", "not in the .fai", id="unknown-contig"),
        pytest.param("", "found 0", id="empty-chunk"),
        pytest.param("chr17\t1\t2\nchr17\t5\t6\n", "found 2", id="two-intervals"),
    ],
)
def test_bad_chunks_fail_with_a_message(tmp_path: Path, bed: str, message: str) -> None:
    out = _pad(tmp_path, bed)
    assert out.returncode == 1
    assert message in out.stderr

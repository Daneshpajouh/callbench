"""Check that each fixture in tests/data still has the property its README row names."""

import gzip
import json
from pathlib import Path

import pytest
from smk_stub import DATA


def _fastq(name: str) -> list[list[str]]:
    lines = gzip.decompress((DATA / name).read_bytes()).decode().splitlines()
    return [lines[i : i + 4] for i in range(0, len(lines), 4)]


def _vcf_data_lines(name: str) -> list[list[str]]:
    lines = (DATA / name).read_text().splitlines()
    return [line.split("\t") for line in lines if line and not line.startswith("#")]


def test_fastq_pair_has_five_matching_records() -> None:
    r1, r2 = _fastq("reads_R1.fastq.gz"), _fastq("reads_R2.fastq.gz")
    assert len(r1) == len(r2) == 5
    for (n1, s1, plus1, q1), (n2, s2, plus2, q2) in zip(r1, r2, strict=True):
        assert n1.removesuffix("/1") == n2.removesuffix("/2")
        assert n1.startswith("@") and n1.endswith("/1") and n2.endswith("/2")
        assert plus1 == plus2 == "+"
        assert len(s1) == len(q1) and len(s2) == len(q2)
        assert set(s1 + s2) <= set("ACGT")


def test_fastp_report_counts_the_fastq_pairs() -> None:
    report = json.loads((DATA / "fastp.json").read_text())
    reads = 2 * len(_fastq("reads_R1.fastq.gz"))
    assert report["summary"]["before_filtering"]["total_reads"] == reads
    bases = sum(len(r[1]) for name in ("reads_R1", "reads_R2") for r in _fastq(f"{name}.fastq.gz"))
    assert report["summary"]["before_filtering"]["total_bases"] == bases


def test_header_only_vcf_has_a_header_and_no_records() -> None:
    text = (DATA / "header_only.vcf").read_text()
    assert text.startswith("##fileformat=VCFv4.2") and "#CHROM" in text
    assert _vcf_data_lines("header_only.vcf") == []


def test_multiallelic_vcf_has_a_site_with_two_alt_alleles() -> None:
    alts = [r[4] for r in _vcf_data_lines("multiallelic.vcf")]
    assert any(len(a.split(",")) == 2 for a in alts)


def test_malformed_vcf_has_a_data_line_with_the_wrong_column_count() -> None:
    header_cols = next(
        len(line.split("\t"))
        for line in (DATA / "malformed_columns.vcf").read_text().splitlines()
        if line.startswith("#CHROM")
    )
    counts = [len(r) for r in _vcf_data_lines("malformed_columns.vcf")]
    assert header_cols in counts and any(c != header_cols for c in counts)


def test_missing_info_vcf_has_a_dot_info_field() -> None:
    infos = [r[7] for r in _vcf_data_lines("missing_info.vcf")]
    assert "." in infos and any(i != "." for i in infos)


def test_bed_prefix_pair_differs_only_by_the_prefix() -> None:
    with_chr = (DATA / "with_chr_prefix.bed").read_text()
    assert with_chr.replace("chr", "") == (DATA / "without_chr_prefix.bed").read_text()
    assert "chr" not in (DATA / "without_chr_prefix.bed").read_text()


def test_empty_bed_is_zero_bytes() -> None:
    assert (DATA / "empty.bed").stat().st_size == 0


def test_crlf_bed_uses_crlf_on_every_line() -> None:
    raw = (DATA / "crlf.bed").read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n") > 0


def test_gzipped_bed_decompresses_to_the_plain_bed() -> None:
    assert (
        gzip.decompress((DATA / "regions.bed.gz").read_bytes())
        == (DATA / "regions.bed").read_bytes()
    )


def test_mosdepth_summaries_differ_by_the_total_region_row() -> None:
    with_total = (DATA / "mosdepth_with_total_region.summary.txt").read_text()
    without = (DATA / "mosdepth_without_total_region.summary.txt").read_text()
    assert "total_region" in with_total and "total_region" not in without
    assert "\ntotal\t" in without


def test_benchmark_fixture_is_na_in_every_resource_column() -> None:
    header, row = (DATA / "benchmark_with_na.tsv").read_text().splitlines()
    values = dict(zip(header.split("\t"), row.split("\t"), strict=True))
    resource = [v for k, v in values.items() if k not in ("s", "h:m:s")]
    assert resource and set(resource) == {"NA"}
    assert float(values["s"]) > 0


def test_clinvar_fixture_has_a_header_and_zero_rows() -> None:
    assert (DATA / "clinvar_zero_rows.tsv").read_text().splitlines() == [
        "chrom\tpos\tref\talt\tgt\tclinvar_id\tclnsig\tclnrevstat\tgeneinfo"
    ]


def test_accuracy_pair_has_the_same_keys_and_an_na_row() -> None:
    def keys(name: str) -> list[tuple[str, ...]]:
        rows = [ln.split("\t") for ln in (DATA / name).read_text().splitlines()[1:]]
        return [tuple(r[:4]) for r in rows]

    assert keys("accuracy_expected.tsv") == keys("accuracy_observed_with_na.tsv")
    assert "NA" in (DATA / "accuracy_observed_with_na.tsv").read_text()


def test_samtools_excerpt_has_summary_and_other_sections() -> None:
    lines = (DATA / "samtools_stats.txt").read_text().splitlines()
    assert any(ln.startswith("SN\t") for ln in lines) and any(
        ln.startswith("FFQ\t") for ln in lines
    )


@pytest.mark.parametrize("path", sorted(DATA.iterdir()), ids=lambda p: p.name)
def test_every_fixture_is_listed_in_the_readme(path: Path) -> None:
    if path.name in ("README.md", ".gitattributes"):
        return
    assert f"`{path.name}`" in (DATA / "README.md").read_text()

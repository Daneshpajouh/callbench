"""The genotype filters of the normalise rules, on calls that use the second ALT allele."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(shutil.which("bcftools") is None, reason="bcftools not on PATH")

# Reference base at every position is A ("ACGT" repeats, positions 1, 5, 9, ... are A).
VCF = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=400>
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS
chr1\t49\t.\tA\tC,G\t50\tPASS\t.\tGT\t0/2
chr1\t101\t.\tA\tC,G\t50\tPASS\t.\tGT\t1/2
chr1\t149\t.\tA\tC,G\t50\tPASS\t.\tGT\t0/1
chr1\t201\t.\tA\tC\t50\tPASS\t.\tGT\t0/0
chr1\t249\t.\tA\tC\t50\tPASS\t.\tGT\t1/1
chr1\t301\t.\tA\tC,G\t50\tPASS\t.\tGT\t2/2
"""


def rule_filters(rule_file: str) -> list[str]:
    """The -i expressions of `bcftools view` in a rule file, with {params} terms removed."""
    text = (ROOT / "workflow" / "rules" / rule_file).read_text()
    exprs = re.findall(r"bcftools view [^|]*?-i '([^']+)'", text)
    return [re.sub(r"\s*&&\s*\{params\.\w+\}", "", e).replace('\\"', '"') for e in exprs]


@pytest.mark.parametrize("rule_file", ["call.smk", "evaluate.smk"])
def test_second_allele_calls_kept_and_reference_records_dropped(
    tmp_path: Path, rule_file: str
) -> None:
    pre, post = rule_filters(rule_file)
    ref = tmp_path / "ref.fa"
    ref.write_text(">chr1\n" + "ACGT" * 100 + "\n")
    subprocess.run(["bcftools", "faidx", str(ref)], check=False, capture_output=True)
    vcf = tmp_path / "calls.vcf"
    vcf.write_text(VCF)
    cmd = (
        f"bcftools view -i '{pre}' -Ou {vcf}"
        f" | bcftools norm -f {ref} -m -any -Ou"
        f" | bcftools view -i '{post}' -Ou"
        " | bcftools query -f '%POS %ALT [%GT]\\n'"
    )
    out = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True).stdout
    assert out.splitlines() == [
        "49 G 0/1",
        "101 C 1/0",
        "101 G 0/1",
        "149 C 0/1",
        "249 C 1/1",
        "301 G 1/1",
    ]

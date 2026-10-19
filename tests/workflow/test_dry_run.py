"""Dry-run the main configuration: the DAG must build and name the core rules."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SNAKEMAKE = Path(sys.executable).parent / "snakemake"
REFERENCE = ROOT / "resources" / "full" / "reference" / "GRCh38_chr13_chr17.fa"

pytestmark = [
    pytest.mark.workflow,
    pytest.mark.skipif(
        not REFERENCE.exists(), reason=f"{REFERENCE.relative_to(ROOT)} has not been fetched"
    ),
]


def test_dry_run_builds_the_dag_and_names_the_core_rules() -> None:
    # --nolock and --ignore-incomplete keep the check read-only when a real run is
    # using the same working directory: it neither waits for that run's lock nor
    # fails on the half-written outputs of jobs that are still going.
    result = subprocess.run(
        [str(SNAKEMAKE), "-n", "--nolock", "--ignore-incomplete", "--quiet", "rules"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output[-3000:]
    for rule in ("bwa_mem", "vcfeval"):
        assert rule in output, f"{rule} missing from the dry-run output"

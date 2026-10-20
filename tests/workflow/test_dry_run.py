"""Dry-run the main configuration: the DAG must build and name the core rules.

Where the full-size data has been fetched, the dry run uses this checkout and
its data. Elsewhere, CI included, it runs in a temporary working directory that
holds a copy of config/ and an empty file at every path under resources/ that
the config or the sample sheet names. A dry run only checks that inputs exist,
so the DAG builds the same way on the stand-ins.
"""

import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SNAKEMAKE = Path(sys.executable).parent / "snakemake"
REFERENCE = ROOT / "resources" / "full" / "reference" / "GRCh38_chr13_chr17.fa"

pytestmark = pytest.mark.workflow


def _resource_paths(node: Any) -> Iterator[str]:
    """Every string under resources/ anywhere in a parsed config or table."""
    if isinstance(node, dict):
        for value in node.values():
            yield from _resource_paths(value)
    elif isinstance(node, list):
        for value in node:
            yield from _resource_paths(value)
    elif isinstance(node, str) and node.startswith("resources/"):
        yield node


def _stand_in_inputs(workdir: Path) -> None:
    config = yaml.safe_load((workdir / "config" / "config.yaml").read_text())
    # Read the sheet as workflow/rules/common.smk does.
    samples = pd.read_csv(workdir / config["samples"], sep="\t", dtype=str, comment="#")
    paths = set(_resource_paths(config))
    paths.update(_resource_paths(samples.fillna("").to_numpy().ravel().tolist()))
    for path in paths:
        (workdir / path).parent.mkdir(parents=True, exist_ok=True)
        (workdir / path).touch()


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    if REFERENCE.exists():
        return ROOT
    shutil.copytree(ROOT / "config", tmp_path / "config")
    _stand_in_inputs(tmp_path)
    return tmp_path


def test_dry_run_builds_the_dag_and_names_the_core_rules(workdir: Path) -> None:
    # In the checkout, --nolock and --ignore-incomplete keep the check read-only
    # when a real run is using it: it neither waits for that run's lock nor
    # fails on the half-written outputs of jobs that are still going.
    shared = ["--nolock", "--ignore-incomplete"] if workdir == ROOT else []
    snakefile = str(ROOT / "workflow" / "Snakefile")
    result = subprocess.run(
        [str(SNAKEMAKE), "-n", *shared, "--quiet", "rules", "-s", snakefile, "-d", str(workdir)],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output[-3000:]
    for rule in ("bwa_mem", "vcfeval"):
        assert rule in output, f"{rule} missing from the dry-run output"

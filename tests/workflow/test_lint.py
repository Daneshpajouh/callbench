"""Workflow lint: snakemake --lint and snakefmt must accept the workflow as it stands."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BIN = Path(sys.executable).parent

pytestmark = pytest.mark.workflow


def _run(*command: str) -> tuple[int, str]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)
    return result.returncode, result.stdout + result.stderr


def test_snakemake_lint_is_clean() -> None:
    code, output = _run(str(BIN / "snakemake"), "--lint")
    assert code == 0, output[-3000:]
    assert "Congratulations" in output


def test_snakefmt_check_leaves_the_workflow_unchanged() -> None:
    code, output = _run(str(BIN / "snakefmt"), "--check", "workflow")
    assert code == 0, output[-3000:]

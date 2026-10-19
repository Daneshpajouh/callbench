import runpy
import sys

import psutil
import pytest
from smk_stub import ROOT

SHIM = ROOT / "tools" / "snakemake_macos.py"


def test_shim_adds_a_per_process_io_counters_that_raises_not_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Remove the attribute first so the test behaves the same on macOS and Linux.
    monkeypatch.delattr(psutil.Process, "io_counters", raising=False)
    runpy.run_path(str(SHIM))
    with pytest.raises(NotImplementedError, match="per-process I/O"):
        psutil.Process().io_counters()


def test_shim_leaves_a_native_io_counters_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    def native(self: psutil.Process) -> str:
        return "native"

    monkeypatch.setattr(psutil.Process, "io_counters", native, raising=False)
    runpy.run_path(str(SHIM))
    assert psutil.Process.io_counters is native


def test_script_exits_with_the_snakemake_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("snakemake.cli.main", lambda: 3)
    monkeypatch.setattr(sys, "argv", ["snakemake_macos.py"])
    with pytest.raises(SystemExit) as info:
        runpy.run_path(str(SHIM), run_name="__main__")
    assert info.value.code == 3

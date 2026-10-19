"""Run Snakemake with a psutil shim so the benchmark directive works on macOS.

psutil has no Process.io_counters on macOS. Snakemake 9.27's benchmark sampler
calls it, gets AttributeError, treats that as "process exited" and drops the
whole sample, so every benchmark file has NA for memory and CPU. Raising
NotImplementedError instead is the path Snakemake already handles: it stops
asking for I/O and keeps the memory and CPU numbers. Linux hosts (and so Slurm
runs) do not need this. See docs/operations/postmortems/2026-10-19-benchmark-na-on-macos.md.
"""

import sys

import psutil

if not hasattr(psutil.Process, "io_counters"):

    def _io_counters_unavailable(self: psutil.Process) -> None:
        raise NotImplementedError("psutil does not report per-process I/O on this OS")

    psutil.Process.io_counters = _io_counters_unavailable

from snakemake.cli import main

if __name__ == "__main__":
    sys.exit(main())

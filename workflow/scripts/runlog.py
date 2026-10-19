"""Run manifest (written before the first job) and run summary (written at the end).

Called from the onstart, onsuccess and onerror handlers in the Snakefile, not
from a rule, so it runs once per invocation in the main Snakemake process.
"""

import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

RUN_DIR = Path("results/run")


def sha256(path: str | Path, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(block):
            h.update(chunk)
    return h.hexdigest()


def git_state(repo: Path) -> dict[str, Any]:
    """Commit and dirty flag; both None when git is absent (slim containers)."""

    def run(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
        ).stdout.strip()

    try:
        commit = run("rev-parse", "HEAD")
    except FileNotFoundError:
        return {"commit": None, "dirty": None}
    return {
        "commit": commit or None,
        "dirty": bool(run("status", "--porcelain")) if commit else None,
    }


def config_inputs(config: dict[str, Any], samples: Iterable[dict[str, str]]) -> list[str]:
    """Every input file named by the config or the samplesheet."""
    paths = [config["reference"]["fasta"], config["regions"], config["clinvar"]["vcf"]]
    paths += list(config["evaluation"]["stratifications"].values())
    for row in samples:
        paths += [row[k] for k in ("fq1", "fq2", "truth_vcf", "truth_bed") if row.get(k)]
    return paths


def env_pins(env_dir: Path) -> dict[str, list[str]]:
    pins = {}
    for f in sorted(env_dir.glob("*.yaml")):
        deps = [
            line.strip()[2:]
            for line in f.read_text().splitlines()
            if line.startswith("  - ") and "=" in line
        ]
        pins[f.stem] = deps
    return pins


def write_manifest(
    config: dict[str, Any],
    samples: list[dict[str, str]],
    basedir: Path,
    snakemake_version: str,
    run_dir: Path = RUN_DIR,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    inputs = []
    for p in config_inputs(config, samples):
        entry: dict[str, Any] = {"path": p}
        if os.path.exists(p):
            entry |= {"bytes": os.path.getsize(p), "sha256": sha256(p)}
        else:
            entry["missing"] = True
        inputs.append(entry)
    manifest = {
        "start_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "snakemake": snakemake_version,
        "git": git_state(basedir.parent),
        "command": sys.argv,
        "config": config,
        "conda_envs": env_pins(basedir / "envs"),
        "inputs": inputs,
    }
    out = run_dir / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    return out


def write_summary(
    status: str,
    targets: list[str],
    benchmark_dir: Path = Path("benchmarks"),
    log_dir: Path = Path("logs"),
    run_dir: Path = RUN_DIR,
) -> Path:
    from profiling_table import collect, per_rule_summary

    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "manifest.json"
    start = None
    if manifest_path.exists():
        start = json.loads(manifest_path.read_text()).get("start_utc")
    end = dt.datetime.now(dt.UTC)
    wall = (end - dt.datetime.fromisoformat(start)).total_seconds() if start else None
    per_rule = []
    if benchmark_dir.exists():
        per_rule = per_rule_summary(collect(benchmark_dir)).to_dict(orient="records")
    outputs = [
        {"path": t, "bytes": os.path.getsize(t), "sha256": sha256(t)}
        if os.path.exists(t)
        else {"path": t, "missing": True}
        for t in targets
    ]
    summary = {
        "status": status,
        "start_utc": start,
        "end_utc": end.isoformat(timespec="seconds"),
        "wall_s": round(wall, 1) if wall is not None else None,
        "per_rule": per_rule,
        "outputs": outputs,
        "logs": sorted(str(p) for p in log_dir.rglob("*.log")) if log_dir.exists() else [],
    }
    out = run_dir / "summary.json"
    out.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return out

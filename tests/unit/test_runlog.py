import hashlib
import json
from pathlib import Path

import pytest
from runlog import config_inputs, env_pins, sha256, write_manifest, write_summary

HEADER = "s\th:m:s\tmax_rss\tmax_vms\tmax_uss\tmax_pss\tio_in\tio_out\tmean_load\tcpu_time\n"


def _config(tmp: Path) -> dict[str, object]:
    ref = tmp / "ref.fa"
    ref.write_text(">chr1\nACGT\n")
    return {
        "reference": {"fasta": str(ref)},
        "regions": str(tmp / "regions.bed"),
        "clinvar": {"vcf": str(tmp / "missing_clinvar.vcf.gz")},
        "evaluation": {"stratifications": {"segdups": str(tmp / "segdups.bed")}},
    }


def test_sha256_matches_hashlib(tmp_path: Path) -> None:
    f = tmp_path / "x"
    f.write_bytes(b"ACGT" * 1000)
    assert sha256(f, block=7) == hashlib.sha256(b"ACGT" * 1000).hexdigest()


def test_config_inputs_skips_empty_truth_columns(tmp_path: Path) -> None:
    rows = [{"fq1": "a.fq.gz", "fq2": "b.fq.gz", "truth_vcf": "", "truth_bed": ""}]
    paths = config_inputs(_config(tmp_path), rows)
    assert "a.fq.gz" in paths and "" not in paths


def test_env_pins_reads_pinned_dependencies(tmp_path: Path) -> None:
    (tmp_path / "bcftools.yaml").write_text(
        "channels:\n  - bioconda\ndependencies:\n  - bcftools=1.23.1\n"
    )
    assert env_pins(tmp_path) == {"bcftools": ["bcftools=1.23.1"]}


def test_manifest_hashes_present_inputs_and_flags_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workflow" / "envs").mkdir(parents=True)
    out = write_manifest(_config(tmp_path), [], tmp_path / "workflow", "9.27.0")
    m = json.loads(out.read_text())
    by_path = {i["path"]: i for i in m["inputs"]}
    assert by_path[str(tmp_path / "ref.fa")]["bytes"] == len(">chr1\nACGT\n")
    assert by_path[str(tmp_path / "missing_clinvar.vcf.gz")]["missing"] is True
    assert m["snakemake"] == "9.27.0"


def test_summary_reports_status_rules_outputs_and_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "benchmarks" / "fastp").mkdir(parents=True)
    (tmp_path / "benchmarks" / "fastp" / "HG002.tsv").write_text(
        HEADER + "25.1\t0:00:25\t1195.8\t1\t1\t0\t-\t-\t94\t24.6\n"
    )
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "fastp.log").write_text("ok\n")
    (tmp_path / "out.tsv").write_text("x\n")
    s = json.loads(write_summary("error", ["out.tsv", "not_made.tsv"]).read_text())
    assert s["status"] == "error"
    assert s["per_rule"][0]["rule"] == "fastp"
    assert s["outputs"][1] == {"path": "not_made.tsv", "missing": True}
    assert s["logs"] == ["logs/fastp.log"]


def test_git_state_without_git_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from runlog import git_state

    monkeypatch.setenv("PATH", str(tmp_path))
    assert git_state(tmp_path) == {"commit": None, "dirty": None}

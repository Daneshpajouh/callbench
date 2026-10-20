"""One row per sample from fastp JSON, samtools stats and mosdepth summaries."""

import json
from typing import Any

import pandas as pd
from logsetup import log_failures, read_tsv, rule_logger


def fastp_metrics(path: str) -> dict[str, float]:
    try:
        with open(path) as fh:
            d = json.load(fh)
        before = d["summary"]["before_filtering"]
        after = d["summary"]["after_filtering"]
        reads_raw, reads_after, q30 = before["total_reads"], after["total_reads"], after["q30_rate"]
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}:{exc.lineno}: invalid JSON: {exc.msg}") from exc
    except KeyError as exc:
        raise ValueError(f"{path}: fastp report has no {exc.args[0]!r} entry") from exc
    return {
        "reads_raw": reads_raw,
        "reads_after_fastp": reads_after,
        "q30_rate_after": round(q30, 4),
        "duplication_rate_fastp": round(d.get("duplication", {}).get("rate", float("nan")), 4),
    }


def samtools_sn(path: str) -> dict[str, float]:
    wanted = {
        "reads mapped:": "reads_mapped",
        "reads duplicated:": "reads_duplicated",
        "error rate:": "error_rate",
        "insert size average:": "insert_size_mean",
        "reads properly paired:": "reads_properly_paired",
    }
    out: dict[str, float] = {}
    has_content = False
    with open(path) as fh:
        for lineno, line in enumerate(fh, start=1):
            has_content = has_content or bool(line.strip())
            if not line.startswith("SN\t"):
                continue
            # SN lines are never the last lines samtools stats writes, so one
            # with no newline was cut inside its value.
            if not line.endswith("\n"):
                raise ValueError(f"{path}:{lineno}: file ends inside an SN line (cut short?)")
            f = line.rstrip("\n").split("\t")
            if len(f) < 3:
                raise ValueError(
                    f"{path}:{lineno}: expected SN, key and value columns, got {len(f)}"
                )
            if f[1] in wanted:
                try:
                    out[wanted[f[1]]] = float(f[2])
                except ValueError:
                    raise ValueError(
                        f"{path}:{lineno}: {f[1]!r} is not numeric: {f[2]!r}"
                    ) from None
    if not has_content:
        raise ValueError(f"{path}: empty file")
    # samtools stats writes every one of these, as 0 for an empty BAM, so a
    # missing key means the file was cut short, not that the value is absent.
    missing = [key for key, name in wanted.items() if name not in out]
    if missing:
        raise ValueError(
            f"{path}: samtools stats summary has no {', '.join(repr(k) for k in missing)}"
            " (file cut short?)"
        )
    return out


def mosdepth_mean(path: str) -> dict[str, float]:
    df = read_tsv(path)
    # With --by, mosdepth adds a total_region row; without it only total exists.
    for label in ("total_region", "total"):
        rows = df[df["chrom"] == label]
        if len(rows):
            row = rows.iloc[0]
            break
    else:
        raise ValueError(f"{path}: no total_region or total row in the mosdepth summary")
    return {"mean_depth_regions": round(float(row["mean"]), 2)}


def main(smk: Any) -> None:
    log = rule_logger(smk)
    with log_failures(log):
        rows = []
        for sample, fp, st, md in zip(
            smk.params.samples, smk.input.fastp, smk.input.stats, smk.input.mosdepth, strict=True
        ):
            log.info("reading %s, %s and %s for %s", fp, st, md, sample)
            row: dict[str, Any] = {"sample": sample}
            row.update(fastp_metrics(fp))
            row.update(samtools_sn(st))
            row.update(mosdepth_mean(md))
            rows.append(row)
        pd.DataFrame(rows).to_csv(smk.output[0], sep="\t", index=False)
        log.info("wrote %d samples to %s", len(rows), smk.output[0])


if "snakemake" in globals():
    main(globals()["snakemake"])

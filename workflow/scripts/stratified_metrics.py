"""Precision, recall and F1 by variant type and GIAB stratum from vcfeval output.

vcfeval writes four VCFs: tp-baseline (truth records matched), fn (truth
records missed), tp (call records matched) and fp (call records unmatched).
Recall uses the truth-side counts and precision the call-side counts, which is
how hap.py and the GA4GH benchmarking definitions count them. A record is
assigned to a stratum when its POS falls in the stratum BED (bcftools -T).
"""

import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from logsetup import log_failures, rule_logger

VARIANT_TYPES = {"SNV": "snps", "INDEL": "indels"}


@dataclass(frozen=True)
class Counts:
    tp_base: int
    fn: int
    tp_call: int
    fp: int

    @property
    def recall(self) -> float | None:
        d = self.tp_base + self.fn
        return self.tp_base / d if d else None

    @property
    def precision(self) -> float | None:
        d = self.tp_call + self.fp
        return self.tp_call / d if d else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None:
            return None
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)


def count_records(vcf: str, vtype: str, bed: str | None) -> int:
    # bcftools exits with an error on an empty targets file, but a stratum that does
    # not overlap the evaluation regions is a valid result: zero records.
    if bed is not None and os.path.getsize(bed) == 0:
        return 0
    cmd = ["bcftools", "view", "-H", "-v", vtype]
    if bed is not None:
        cmd += ["-T", bed]
    cmd.append(vcf)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode:
        raise ValueError(f"{vcf}: bcftools view exited {proc.returncode}: {proc.stderr.strip()}")
    return sum(1 for line in proc.stdout.splitlines() if line)


def fmt(x: float | None) -> str:
    return "NA" if x is None else f"{x:.4f}"


def main(smk: Any) -> None:
    log = rule_logger(smk)
    with log_failures(log):
        write_table(smk, log)


def write_table(smk: Any, log: logging.Logger) -> None:
    strata: dict[str, str | None] = {"all": None}
    strata.update(dict(zip(smk.params.strata, smk.input.strata, strict=True)))
    log.info(
        "reading vcfeval tp-baseline, fn, tp and fp for %s and %d strata",
        smk.wildcards.caller,
        len(strata),
    )
    header = [
        "sample",
        "caller",
        "stratum",
        "type",
        "tp_base",
        "fn",
        "tp_call",
        "fp",
        "recall",
        "precision",
        "f1",
    ]
    rows = ["\t".join(header)]
    for stratum, bed in strata.items():
        for vname, vflag in VARIANT_TYPES.items():
            c = Counts(
                tp_base=count_records(smk.input.tp_base, vflag, bed),
                fn=count_records(smk.input.fn, vflag, bed),
                tp_call=count_records(smk.input.tp, vflag, bed),
                fp=count_records(smk.input.fp, vflag, bed),
            )
            rows.append(
                "\t".join(
                    [
                        smk.wildcards.sample,
                        smk.wildcards.caller,
                        stratum,
                        vname,
                        str(c.tp_base),
                        str(c.fn),
                        str(c.tp_call),
                        str(c.fp),
                        fmt(c.recall),
                        fmt(c.precision),
                        fmt(c.f1),
                    ]
                )
            )
    with open(smk.output[0], "w") as fh:
        fh.write("\n".join(rows) + "\n")
    log.info("wrote %d rows to %s", len(rows) - 1, smk.output[0])


if "snakemake" in globals():
    main(globals()["snakemake"])

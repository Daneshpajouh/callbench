"""Intersect a BED (plain or gzipped) with the evaluation intervals.

Both inputs may be unsorted and overlapping; the output is sorted and merged.
Used for the truth-set confident regions and for each stratification BED.
"""

import gzip
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import IO, Any

Interval = tuple[str, int, int]


def _open(path: str | Path) -> IO[str]:
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt")
    return open(path)


def read_bed(path: str | Path) -> list[Interval]:
    out: list[Interval] = []
    with _open(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            f = line.rstrip("\n").split("\t")
            out.append((f[0], int(f[1]), int(f[2])))
    return out


def merge(intervals: Iterable[Interval]) -> list[Interval]:
    by_chrom: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for c, s, e in intervals:
        if e > s:
            by_chrom[c].append((s, e))
    merged: list[Interval] = []
    for c in sorted(by_chrom):
        cur_s, cur_e = -1, -1
        for s, e in sorted(by_chrom[c]):
            if s > cur_e:
                if cur_e > 0:
                    merged.append((c, cur_s, cur_e))
                cur_s, cur_e = s, e
            else:
                cur_e = max(cur_e, e)
        if cur_e > 0:
            merged.append((c, cur_s, cur_e))
    return merged


def intersect(a: Iterable[Interval], b: Iterable[Interval]) -> list[Interval]:
    """Return the parts of ``a`` covered by ``b`` (sweep over merged inputs)."""
    a_m, b_m = merge(a), merge(b)
    b_by: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for c, s, e in b_m:
        b_by[c].append((s, e))
    out: list[Interval] = []
    for c, s, e in a_m:
        for bs, be in b_by.get(c, []):
            if be <= s:
                continue
            if bs >= e:
                break
            out.append((c, max(s, bs), min(e, be)))
    return merge(out)


def write_bed(intervals: Iterable[Interval], path: str | Path) -> int:
    n = 0
    with open(path, "w") as fh:
        for c, s, e in intervals:
            fh.write(f"{c}\t{s}\t{e}\n")
            n += 1
    return n


def main(smk: Any) -> None:
    result = intersect(read_bed(smk.input[0]), read_bed(smk.input.regions))
    n = write_bed(result, smk.output[0])
    bp = sum(e - s for _, s, e in result)
    with open(smk.log[0], "w") as log:
        print(f"{n} intervals, {bp} bp", file=log)


if "snakemake" in globals():
    main(globals()["snakemake"])

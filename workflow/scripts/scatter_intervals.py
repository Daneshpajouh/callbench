"""Split evaluation intervals into chunks of at most ``chunk_size`` bp.

Each chunk is written as its own BED (0001.bed, 0002.bed, ...) so that the
number of calling jobs follows the size of the target, not a fixed count.
"""

import sys
from pathlib import Path
from typing import Any

Interval = tuple[str, int, int]


def read_bed(path: str | Path) -> list[Interval]:
    out: list[Interval] = []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.startswith(("#", "track", "browser")):
            continue
        chrom, start, end = line.split("\t")[:3]
        out.append((chrom, int(start), int(end)))
    return out


def split_intervals(intervals: list[Interval], chunk_size: int) -> list[Interval]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    chunks: list[Interval] = []
    for chrom, start, end in intervals:
        pos = start
        while pos < end:
            stop = min(pos + chunk_size, end)
            chunks.append((chrom, pos, stop))
            pos = stop
    return chunks


def write_chunks(chunks: list[Interval], outdir: str | Path) -> list[Path]:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (chrom, start, end) in enumerate(chunks, start=1):
        p = out / f"{i:04d}.bed"
        p.write_text(f"{chrom}\t{start}\t{end}\n")
        paths.append(p)
    return paths


def main(smk: Any) -> None:
    chunks = split_intervals(read_bed(smk.input.regions), int(smk.params.chunk_size))
    paths = write_chunks(chunks, smk.output[0])
    with open(smk.log[0], "w") as log:
        print(f"{len(paths)} chunks of at most {smk.params.chunk_size} bp", file=log)


if "snakemake" in globals():
    main(globals()["snakemake"])
elif __name__ == "__main__" and len(sys.argv) == 4:
    write_chunks(split_intervals(read_bed(sys.argv[1]), int(sys.argv[2])), sys.argv[3])

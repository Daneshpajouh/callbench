"""Compare an accuracy table with the expected one and fail on regressions.

Used in CI after the test-profile run. Rows are matched on sample, caller,
stratum and type. A row fails when F1 drops by more than --tolerance, or when
a row in the expected table is missing from the observed one. Gains are
printed but do not fail: a caller upgrade that improves accuracy still needs a
human to update the expected table in the same pull request.

F1 alone misses two kinds of change. A wrong evaluation BED or a stratum file
that stops intersecting can lose truth variants while F1 stays at 1.0, so when
both tables carry tp_base and fn the truth count (tp_base + fn) must match
exactly. A stratum with no expected F1 (no truth variants and no calls) is
not skipped: a false positive appearing there fails the row.
"""

import argparse
import sys

import pandas as pd

KEY = ["sample", "caller", "stratum", "type"]


def _truth(row: pd.Series, suffix: str) -> int | None:
    """tp_base + fn for one side of a merged row, or None when either is absent."""
    values = [
        pd.to_numeric(row.get(f"{c}{suffix}", float("nan")), errors="coerce")
        for c in ("tp_base", "fn")
    ]
    if any(pd.isna(v) for v in values):
        return None
    return int(sum(values))


def compare(observed: pd.DataFrame, expected: pd.DataFrame, tolerance: float) -> list[str]:
    for name, table in (("observed", observed), ("expected", expected)):
        dup = table[table.duplicated(KEY, keep=False)]
        if not dup.empty:
            labels = sorted({"/".join(str(r[k]) for k in KEY) for _, r in dup.iterrows()})
            return [f"{label}: repeated in the {name} table" for label in labels]
    merged = expected.merge(observed, on=KEY, how="left", suffixes=("_exp", "_obs"), indicator=True)
    problems = []
    for _, r in merged.iterrows():
        label = "/".join(str(r[k]) for k in KEY)
        # Checked first: an expected row with no F1 would otherwise be skipped below.
        if r["_merge"] == "left_only":
            problems.append(f"{label}: missing from observed table")
            continue
        f1_exp = pd.to_numeric(r["f1_exp"], errors="coerce")
        f1_obs = pd.to_numeric(r["f1_obs"], errors="coerce")
        truth_exp, truth_obs = _truth(r, "_exp"), _truth(r, "_obs")
        if truth_exp is not None and truth_obs is not None and truth_obs != truth_exp:
            problems.append(f"{label}: truth count {truth_obs} != expected {truth_exp}")
        if pd.isna(f1_exp):
            fp_obs = pd.to_numeric(r.get("fp_obs", float("nan")), errors="coerce")
            if pd.notna(fp_obs) and fp_obs > 0:
                problems.append(f"{label}: {int(fp_obs)} false positives where none were expected")
            continue
        if pd.isna(f1_obs):
            problems.append(f"{label}: missing or NA in observed table")
        # The slack keeps a drop of exactly --tolerance from failing on float rounding:
        # 0.5006 - 0.005 evaluates to 0.49560000000000004, so 0.4956 would be flagged.
        elif f1_obs < f1_exp - tolerance - 1e-9:
            problems.append(f"{label}: F1 {f1_obs:.4f} < expected {f1_exp:.4f}")
        elif abs(f1_obs - f1_exp) > 1e-9:
            print(f"{label}: F1 changed {f1_exp:.4f} -> {f1_obs:.4f} (within tolerance)")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("observed")
    ap.add_argument("expected")
    ap.add_argument("--tolerance", type=float, default=0.005)
    args = ap.parse_args(argv)
    problems = compare(
        pd.read_csv(args.observed, sep="\t"),
        pd.read_csv(args.expected, sep="\t"),
        args.tolerance,
    )
    for p in problems:
        print(f"REGRESSION {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

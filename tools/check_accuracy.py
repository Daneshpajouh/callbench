"""Compare an accuracy table with the expected one and fail on regressions.

Used in CI after the test-profile run. Rows are matched on sample, caller,
stratum and type. A row fails when F1 drops by more than --tolerance, or when
a row in the expected table is missing from the observed one. Gains are
printed but do not fail: a caller upgrade that improves accuracy still needs a
human to update the expected table in the same pull request.
"""

import argparse
import sys

import pandas as pd

KEY = ["sample", "caller", "stratum", "type"]


def compare(observed: pd.DataFrame, expected: pd.DataFrame, tolerance: float) -> list[str]:
    merged = expected.merge(observed, on=KEY, how="left", suffixes=("_exp", "_obs"))
    problems = []
    for _, r in merged.iterrows():
        label = "/".join(str(r[k]) for k in KEY)
        f1_exp = pd.to_numeric(r["f1_exp"], errors="coerce")
        f1_obs = pd.to_numeric(r["f1_obs"], errors="coerce")
        if pd.isna(f1_exp):
            continue
        if pd.isna(f1_obs):
            problems.append(f"{label}: missing or NA in observed table")
        elif f1_obs < f1_exp - tolerance:
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

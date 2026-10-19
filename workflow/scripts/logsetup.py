"""Logging and input-error helpers shared by the rule scripts.

Snakemake puts the script's own directory on ``sys.path``, so a rule script
can ``from logsetup import ...`` without any packaging.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

FORMAT = "%(asctime)s %(levelname)s rule=%(rule)s sample=%(sample)s %(message)s"


class _RuleContext(logging.Filter):
    """Stamp the rule and sample on every record so the format string stays static."""

    def __init__(self, rule: str, sample: str) -> None:
        super().__init__()
        self.rule, self.sample = rule, sample

    def filter(self, record: logging.LogRecord) -> bool:
        record.rule, record.sample = self.rule, self.sample
        return True


def rule_logger(smk: Any) -> logging.Logger:
    """Return a logger that appends to ``smk.log[0]`` and tags lines with rule and sample."""
    name = str(smk.log[0])
    levels = logging.getLevelNamesMapping()
    level = str(smk.config.get("log_level", "INFO")).upper()
    if level not in levels:
        raise ValueError(f"log_level must be one of {sorted(levels)}, got {level!r}")
    logger = logging.getLogger(f"rule.{smk.rule}.{name}")
    # A second call in one process (tests, or a script that runs twice) must not
    # stack handlers and print every line twice.
    for old in list(logger.handlers):
        logger.removeHandler(old)
        old.close()
    handler = logging.FileHandler(name, mode="a")
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.addFilter(_RuleContext(str(smk.rule), str(smk.wildcards.get("sample", "-"))))
    logger.addHandler(handler)
    logger.setLevel(levels[level])
    logger.propagate = False
    return logger


@contextmanager
def log_failures(log: logging.Logger) -> Iterator[None]:
    """Write any exception to the log at ERROR level, then let it propagate."""
    try:
        yield
    except Exception as exc:
        log.error("%s: %s", type(exc).__name__, exc)
        raise


def read_tsv(path: str | Path, *, as_str: bool = False) -> pd.DataFrame:
    """Read a tab-separated table, naming the file when it is empty or malformed."""
    try:
        if as_str:
            return pd.read_csv(path, sep="\t", dtype=str)
        return pd.read_csv(path, sep="\t")
    except pd.errors.EmptyDataError:
        raise ValueError(f"{path}: empty file, expected a header line") from None
    except pd.errors.ParserError as exc:
        raise ValueError(f"{path}: malformed TSV: {exc}") from exc

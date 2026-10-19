import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The workflow scripts and tools/check_accuracy.py are plain files run by
# Snakemake's script directive or from the command line, not an installed
# package; put their directories on the path so tests can import them.
for directory in (ROOT / "workflow" / "scripts", ROOT / "tools"):
    sys.path.insert(0, str(directory))


@pytest.fixture(autouse=True)
def close_rule_loggers() -> Iterator[None]:
    """Close the log files that rule_logger opens so no test leaves a handle behind."""
    yield
    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if name.startswith("rule.") and isinstance(logger, logging.Logger):
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
                handler.close()

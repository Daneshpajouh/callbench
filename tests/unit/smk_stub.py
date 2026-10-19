"""Stand-ins for the ``snakemake`` object that Snakemake injects into script files."""

import runpy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tests" / "data"
SCRIPTS = ROOT / "workflow" / "scripts"


class Files(list[str]):
    """List of paths that is also readable by name, like ``snakemake.input``.

    The BED intersection script reads its first input by position and the
    evaluation regions by name, so a plain list or namespace is not enough.
    """

    def __init__(self, *items: str, **named: str) -> None:
        super().__init__([*items, *named.values()])
        self.__dict__.update(named)


class Wildcards(dict[str, str]):
    """Mapping with attribute access, like ``snakemake.wildcards``."""

    def __getattr__(self, name: str) -> str:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


def make_smk(tmp_path: Path, rule: str, **sections: Any) -> SimpleNamespace:
    """Build a ``snakemake`` stand-in with the fields every rule script reads."""
    fields: dict[str, Any] = {
        "rule": rule,
        "config": {},
        "wildcards": Wildcards(),
        "log": [str(tmp_path / f"{rule}.log")],
    }
    fields.update(sections)
    return SimpleNamespace(**fields)


def run_as_rule_script(name: str, smk: Any) -> None:
    """Execute a script file the way Snakemake does: with ``snakemake`` as a global.

    Going through runpy covers the module-level dispatch line that a plain
    import skips, and proves the script has no import-time dependence on
    anything but the injected object.
    """
    runpy.run_path(str(SCRIPTS / f"{name}.py"), init_globals={"snakemake": smk})

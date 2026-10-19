import sys
from pathlib import Path

# The workflow scripts are plain files run by Snakemake's script directive, not
# an installed package; put their directory on the path so tests can import them.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workflow" / "scripts"))

"""Bootstrap the local src package for categorized script entrypoints only."""

import sys
from pathlib import Path


def run(module):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from mineprot_toolkit.cli import execute

    return execute(module)

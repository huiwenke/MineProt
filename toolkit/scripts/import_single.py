#!/usr/bin/env python3
"""Source-checkout entrypoint for import_single."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runner = Path(__file__).resolve().parent / "_run.py"
    raise SystemExit(runpy.run_path(str(runner))["run"]("import_single"))

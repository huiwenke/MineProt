#!/usr/bin/env python3
"""Source-checkout entrypoint for misc.preprocess_pdb."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runner = Path(__file__).resolve().parents[1] / "_run.py"
    raise SystemExit(runpy.run_path(str(runner))["run"]("misc.preprocess_pdb"))

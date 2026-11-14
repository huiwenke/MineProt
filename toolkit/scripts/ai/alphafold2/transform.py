#!/usr/bin/env python3
"""Source-checkout entrypoint for ai.alphafold2.transform."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runner = Path(__file__).resolve().parents[2] / "_run.py"
    raise SystemExit(runpy.run_path(str(runner))["run"]("ai.alphafold2.transform"))

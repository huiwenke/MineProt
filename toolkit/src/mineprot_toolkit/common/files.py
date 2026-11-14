"""Text readers shared by alignment and confidence-processing commands."""

import bz2
import gzip
import lzma
from pathlib import Path


def open_text(path):
    path = Path(path)
    opener = {".gz": gzip.open, ".xz": lzma.open, ".bz2": bz2.open}.get(path.suffix, open)
    return opener(path, "rt", encoding="utf-8")

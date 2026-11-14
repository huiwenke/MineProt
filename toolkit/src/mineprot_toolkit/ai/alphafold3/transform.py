"""Collect AlphaFold3 structures and merge confidence files entirely locally."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Result ZIP, a single result directory, or a directory of result subdirectories",
    )
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output directory")
    parser.add_argument(
        "-f", "--force", action="store_true", help="Overwrite existing output pairs"
    )
    return parser


def has_models(directory):
    return any(directory.glob("*_model_0.cif")) or any(directory.glob("*_model.cif"))


def extract_result(archive, destination):
    """Extract a ZIP, then unwrap an optional single enclosing result directory."""
    with ZipFile(archive) as zipped:
        root = destination.resolve()
        for entry in zipped.infolist():
            if not (root / entry.filename).resolve().is_relative_to(root):
                raise ValueError(
                    f"ZIP member is outside the extraction directory: {entry.filename}"
                )
        zipped.extractall(destination)
    directory = destination
    while not has_models(directory) and not (directory / "msas").is_dir():
        children = [
            path
            for path in directory.iterdir()
            if path.is_dir() and not path.name.startswith(".") and path.name != "__MACOSX"
        ]
        if len(children) != 1:
            break
        directory = children[0]
    return directory


def read_confidences(path):
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def transform_directory(directory, output, force=False, seen=None):
    """Pair files by model prefix, preserving CIF bytes and all confidence fields."""
    if (directory / "msas").is_dir():
        model_suffix = "_model_0.cif"
        data_suffix = "_full_data_0.json"
        summary_suffix = "_summary_confidences_0.json"
    else:
        model_suffix = "_model.cif"
        data_suffix = "_confidences.json"
        summary_suffix = "_summary_confidences.json"
    models = sorted(path for path in directory.glob("*" + model_suffix) if path.is_file())
    if not models:
        raise ValueError(f"No *{model_suffix} found in {directory}")
    seen = set() if seen is None else seen
    for model in models:
        name = model.name.removesuffix(model_suffix)
        if not name or name in (".", ".."):
            raise ValueError(f"Invalid model name: {model.name}")
        if name in seen:
            raise ValueError(f"Duplicate output name across results: {name}")
        seen.add(name)
        data_path = directory / (name + data_suffix)
        summary_path = directory / (name + summary_suffix)
        # Validate both files before creating either output.
        merged = {**read_confidences(data_path), **read_confidences(summary_path)}
        cif_path, json_path = output / (name + ".cif"), output / (name + ".json")
        if not force and (cif_path.exists() or json_path.exists()):
            if cif_path.is_file() and json_path.is_file():
                print(f"Skipping {name}: output pair already exists")
                continue
            raise FileExistsError(f"Incomplete output pair for {name}; use -f to replace it")
        output.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".alphafold3-", dir=output) as temporary:
            staged = Path(temporary)
            shutil.copyfile(model, staged / "model.cif")
            (staged / "scores.json").write_text(
                json.dumps(merged, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(staged / "model.cif", cif_path)
            os.replace(staged / "scores.json", json_path)
        print(f"Prepared {name}")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if source.is_file():
        try:
            with TemporaryDirectory(prefix="mineprot-alphafold3-") as temporary:
                directory = extract_result(source, Path(temporary))
                transform_directory(directory, output, args.force)
        except BadZipFile as exc:
            raise ValueError(f"Input is not a valid result ZIP: {source}") from exc
        return 0
    if not source.is_dir():
        parser.error("-i must be a result ZIP or an existing directory")
    if has_models(source) or (source / "msas").is_dir():
        transform_directory(source, output, args.force)
        return 0
    directories = sorted(
        path
        for path in source.iterdir()
        if path.is_dir() and not path.name.startswith(".") and path.resolve() != output
    )
    if not directories:
        raise ValueError(f"No AlphaFold3 results or result subdirectories in {source}")
    failures = 0
    seen = set()
    for directory in directories:
        try:
            transform_directory(directory, output, args.force, seen)
        except (OSError, ValueError) as exc:
            failures += 1
            print(f"Error processing {directory.name}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

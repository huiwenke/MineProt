"""Lazy command dispatch shared by installed and source-checkout entrypoints."""

import argparse
import sys
from importlib import import_module

import requests

COMMANDS = {
    "ai": {
        "alphafold2": {"transform": "ai.alphafold2.transform"},
        "alphafold3": {
            "prepare-complex": "ai.alphafold3.prepare_complex",
            "prepare-pair": "ai.alphafold3.prepare_pair",
            "select-max": "ai.alphafold3.select_max",
        },
        "colabfold": {"transform": "ai.colabfold.transform"},
    },
    "batch": {
        "import-repo": "batch.import_repo",
        "import-es": "batch.import_es",
        "prepare-beacon": "batch.prepare_beacon",
    },
    "import-single": "import_single",
    "misc": {
        "export": "misc.export",
        "calculate-neff": "misc.calculate_neff",
        "extract-plddt": "misc.extract_plddt",
        "select-max": "misc.select_max",
        "distribute-files": "misc.distribute_files",
        "convert-pdb": "misc.convert_pdb",
        "preprocess-pdb": "misc.preprocess_pdb",
    },
}


def execute(module, argv=None):
    """Run a command without obscuring its exit status or cancellation."""
    try:
        return import_module("mineprot_toolkit." + module).main(argv)
    except (KeyboardInterrupt, EOFError):
        print(
            "Operation cancelled; inspect server state if an import had started.", file=sys.stderr
        )
        return 130
    except (OSError, ValueError, RuntimeError, requests.RequestException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def build_parser():
    parser = argparse.ArgumentParser(description="MineProt protein curation toolkit")

    def add_commands(parent, commands):
        subparsers = parent.add_subparsers(required=True)
        for name, command in commands.items():
            if isinstance(command, dict):
                child = subparsers.add_parser(name)
                add_commands(child, command)
            else:
                child = subparsers.add_parser(name, add_help=False)
                child.set_defaults(module=command)

    add_commands(parser, COMMANDS)
    return parser


def main(argv=None):
    args, remaining = build_parser().parse_known_args(argv)
    return execute(args.module, remaining)

import argparse
import os
import shutil
from pathlib import Path

from mineprot_toolkit.common.api import pdb2cif
from mineprot_toolkit.common.defaults import CONVERSION_URL


# List arguments
def build_parser():
    parser = argparse.ArgumentParser(
        description="Preprocess your predicted PDB files for curation."
    )
    parser.add_argument("-i", type=str, required=True, help="Path to input folder.")
    parser.add_argument("-o", type=str, help="Path to output folder.")
    parser.add_argument("--url", type=str, default=CONVERSION_URL, help="URL of PDB2CIF API.")
    return parser


def main(argv=None):
    parser = build_parser()
    # Parse arguments
    args = parser.parse_args(argv)
    if not os.path.isdir(args.i):
        parser.error("-i must be an existing directory")
    input_dir = args.i
    if not args.o:
        print("Output parameter -o is unset, using default value (same path as -i).")
        args.o = args.i
    output_dir = args.o
    print("Data will be generated in " + output_dir)
    if not os.path.exists(output_dir):
        print("Output directory " + output_dir + " not exist. Creating ...")
        os.makedirs(output_dir)

    name_list = []
    file_list = os.listdir(input_dir)
    for file_name in file_list:
        if os.path.splitext(file_name)[-1] == ".pdb":
            name_list.append(os.path.splitext(file_name)[0])

    # Convert PDB to CIF
    print("Generating CIF files...")
    for prefix in name_list:
        source = Path(input_dir) / (prefix + ".pdb")
        destination = Path(output_dir) / source.name
        if source.resolve() != destination.resolve():
            shutil.copyfile(source, destination)
        pdb2cif(output_dir, prefix, args.url)

    # All done
    print("Done.")


if __name__ == "__main__":
    raise SystemExit(main())

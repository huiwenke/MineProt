import argparse
import os
import shutil
import zipfile
from tempfile import TemporaryDirectory

from mineprot_toolkit.common.api import pdb2cif
from mineprot_toolkit.common.defaults import CONVERSION_URL
from mineprot_toolkit.common.naming import move_predictions


# List arguments
def build_parser():
    parser = argparse.ArgumentParser(
        description="Preprocess your ColabFold predictions for curation: pick out top-1 model and generate .cif for visualization."
    )
    parser.add_argument(
        "-i", type=str, required=True, help="Path to input folder. THIS ARGUMENT IS MANDATORY."
    )
    parser.add_argument(
        "-o", type=str, required=True, help="Path to output folder. THIS ARGUMENT IS MANDATORY."
    )
    parser.add_argument(
        "-n",
        type=int,
        choices=range(4),
        default=0,
        help="Naming mode: 0: Use prefix; 1: Use name in .a3m; 2: Auto rename; 3: Customize name.",
    )
    parser.add_argument("-z", help="Unzip results.", action="store_true")
    parser.add_argument("-r", help="Use relaxed results.", action="store_true")
    parser.add_argument("-f", help="Force overwrite.", action="store_true")
    parser.add_argument("--url", type=str, default=CONVERSION_URL, help="URL of PDB2CIF API.")
    return parser


def prediction_filename(is_relaxed, file_name):
    """
    Pick out necessary files for curation.
    :param is_relaxed: Marks if the protein is relaxed, bool
    :param file_name: File name to be checked, str
    :return: Flag of whether the file name is valid, str
    """
    relaxed_id = ["_relaxed_rank_001_", "_relaxed_rank_1_"]
    unrelaxed_id = ["_unrelaxed_rank_001_", "_unrelaxed_rank_1_"]
    scores_id = ["_scores_rank_001_", "_unrelaxed_rank_1_"]
    suffix = os.path.splitext(file_name)[-1]
    if suffix == ".a3m":
        return file_name
    try:
        if suffix == ".pdb":
            if is_relaxed:
                for id in relaxed_id:
                    try:
                        file_name.index(id)
                        return file_name.split(id)[0] + suffix
                    except Exception:
                        continue
            else:
                for id in unrelaxed_id:
                    try:
                        file_name.index(id)
                        return file_name.split(id)[0] + suffix
                    except Exception:
                        continue
        if suffix == ".json":
            for id in scores_id:
                try:
                    file_name.index(id)
                    return file_name.split(id)[0] + suffix
                except Exception:
                    continue
        return ""
    except Exception:
        return ""


def stage_prediction(is_zip, is_relaxed, file_name, input_dir, output_dir, existing_files):
    """
    Copy files to temporary folder.
    :param is_zip: Marks if the file should be decompressed, bool
    :param is_relaxed: Marks if the protein is relaxed, bool
    :param input_dir: Copy source directory, str
    :param output_dir: Copy destination directory, str
    :param existing_files: Existing file list for skipping, list
    """
    file_path = os.path.join(input_dir, file_name)
    # Check if we need to decompress input file
    if is_zip:
        if os.path.splitext(file_name)[-1] == ".zip":
            zip_file = zipfile.ZipFile(file_path)
            zip_list = zip_file.infolist()
            for zip_f in zip_list:
                # Check if the given file name is valid and decompress valid file to output directory
                if prediction_filename(is_relaxed, zip_f.filename) != "":
                    zip_f.filename = prediction_filename(is_relaxed, zip_f.filename)
                    if zip_f.filename not in existing_files:
                        zip_file.extract(zip_f, output_dir)
            zip_file.close()
    else:
        # Check if the given file name is valid and copy valid file to output directory
        if (
            prediction_filename(is_relaxed, file_name) != ""
            and prediction_filename(is_relaxed, file_name) not in existing_files
        ):
            output_path = os.path.join(output_dir, prediction_filename(is_relaxed, file_name))
            shutil.copyfile(file_path, output_path)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not os.path.isdir(args.i):
        parser.error("-i must be an existing directory")
    os.makedirs(args.o, exist_ok=True)
    with TemporaryDirectory(prefix="mineprot-colabfold-") as temporary:
        existing = [] if args.f else os.listdir(args.o)
        for filename in sorted(os.listdir(args.i)):
            stage_prediction(args.z, args.r, filename, args.i, temporary, existing)
        names = move_predictions(temporary, args.o, args.n)
    for name in names:
        pdb2cif(args.o, name, args.url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

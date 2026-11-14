import argparse
import json
import os
import pickle
import shutil
from tempfile import TemporaryDirectory

from mineprot_toolkit.common.api import pdb2cif
from mineprot_toolkit.common.defaults import CONVERSION_URL
from mineprot_toolkit.common.naming import move_predictions


# List arguments
def build_parser():
    parser = argparse.ArgumentParser(
        description="Preprocess your AlphaFold2 predictions for curation: pick out top-1 model and generate .cif for visualization."
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
    parser.add_argument("--url", type=str, default=CONVERSION_URL, help="URL of PDB2CIF API.")
    return parser


def stage_prediction(dir_name, input_dir, output_dir):
    """
    Copy files to temporary folder.
    :param input_dir: Copy source directory, str
    :param output_dir: Copy destination directory, str
    """
    file_name = dir_name
    output_path = os.path.join(output_dir, file_name)
    try:
        dir_path = os.path.join(input_dir, dir_name)
        with open(dir_path + "/ranking_debug.json", "r") as fin_json:
            ranked_0 = json.load(fin_json)["order"][0]
    except Exception:
        print("Error: Prediction of " + dir_name + " failed.")
        return
    pkl_path = dir_path + "/result_" + ranked_0 + ".pkl"
    with open(pkl_path, "rb") as stream:
        pkl_data = pickle.load(stream)
    json_data = {"plddt": pkl_data["plddt"].tolist(), "pae": [], "max_pae": 31.75, "ptm": 0}
    try:
        for plddt_i in range(len(json_data["plddt"])):
            json_data["plddt"][plddt_i] = round(json_data["plddt"][plddt_i], 2)
        json_data["pae"] = pkl_data["predicted_aligned_error"].tolist()
        for pae_i in range(len(json_data["pae"])):
            for pae_j in range(len(json_data["pae"])):
                json_data["pae"][pae_i][pae_j] = round(json_data["pae"][pae_i][pae_j])
        json_data["max_pae"] = float(pkl_data["max_predicted_aligned_error"])
        json_data["ptm"] = float(pkl_data["ptm"])
    except Exception:
        print("Warining: Not pTM model. PAE plot will be disabled.")
    with open(output_path + ".json", "w") as fout_json:
        json.dump(json_data, fout_json, separators=(",", ":"))
    shutil.copyfile(dir_path + "/ranked_0.pdb", output_path + ".pdb")
    a3m_path_ids = ["msas/bfd_uniclust_hits.a3m", "msas/bfd_uniref_hits.a3m"]
    for a3m_path_id in a3m_path_ids:
        try:
            with (
                open(dir_path + "/" + a3m_path_id, "r") as fin_a3m,
                open(output_path + ".a3m", "w") as fout_a3m,
            ):
                # fout_a3m.write("# Added by MineProt toolkit\n")
                fout_a3m.write(fin_a3m.read())
            return
        except Exception:
            continue


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not os.path.isdir(args.i):
        parser.error("-i must be an existing directory")
    os.makedirs(args.o, exist_ok=True)
    with TemporaryDirectory(prefix="mineprot-alphafold2-") as temporary:
        for dir_name in sorted(os.listdir(args.i)):
            if os.path.isdir(os.path.join(args.i, dir_name)):
                stage_prediction(dir_name, args.i, temporary)
        names = move_predictions(temporary, args.o, args.n)
    for name in names:
        pdb2cif(args.o, name, args.url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

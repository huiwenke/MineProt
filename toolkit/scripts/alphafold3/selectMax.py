import argparse
import os
import json
import shutil
from collections import defaultdict

def parse_args():
    parser = argparse.ArgumentParser(description="Select subdirectory with highest iptm and copy its files.")
    parser.add_argument('-i', '--input_dirs', nargs='+', required=True, help='Two or more input directories')
    parser.add_argument('-o', '--output_dir', required=True, help='Output directory')
    return parser.parse_args()

def extract_iptm(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data.get('iptm', 0)

def main():
    args = parse_args()
    input_dirs = args.input_dirs
    output_dir = args.output_dir

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Mapping: subdir name -> list of (full subdir path, iptm value)
    iptm_scores = defaultdict(list)

    for input_dir in input_dirs:
        for entry in os.listdir(input_dir):
            subdir_path = os.path.join(input_dir, entry)
            if os.path.isdir(subdir_path):
                for file in os.listdir(subdir_path):
                    if file.endswith('_summary_confidences.json'):
                        json_path = os.path.join(subdir_path, file)
                        try:
                            iptm_value = extract_iptm(json_path)
                            iptm_scores[entry].append((subdir_path, iptm_value))
                        except Exception as e:
                            print(f"Failed to process {json_path}: {e}")
                        break  # Only process one *_summary_confidences.json per subdir

    for subdir_name, sources in iptm_scores.items():
        best_path, best_iptm = max(sources, key=lambda x: x[1])
        dst_subdir = os.path.join(output_dir, subdir_name)
        if not os.path.exists(dst_subdir):
            os.makedirs(dst_subdir)

        for file in os.listdir(best_path):
            src = os.path.join(best_path, file)
            if os.path.isfile(src):  # Only copy regular files
                dst = os.path.join(dst_subdir, file)
                shutil.copy2(src, dst)
                print(f"Copied {file} from {best_path} to {dst_subdir}")
            else:
                print(f"Skipped directory {file} inside {best_path}")

if __name__ == '__main__':
    main()

import argparse
import os
import json
import shutil
from collections import defaultdict

def parse_args():
    parser = argparse.ArgumentParser(description="Select highest plddt JSON files and copy related files.")
    parser.add_argument('-i', '--input_dirs', nargs='+', required=True, help='Two or more input directories')
    parser.add_argument('-o', '--output_dir', required=True, help='Output directory')
    return parser.parse_args()

def compute_plddt_avg(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    plddt_values = data.get('plddt', [])
    if not plddt_values:
        return 0
    return sum(plddt_values) / len(plddt_values)

def main():
    args = parse_args()
    input_dirs = args.input_dirs
    output_dir = args.output_dir

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Mapping: filename -> list of (input_dir, avg_plddt)
    plddt_scores = defaultdict(list)

    for input_dir in input_dirs:
        for file in os.listdir(input_dir):
            if file.endswith('.json'):
                json_path = os.path.join(input_dir, file)
                try:
                    avg = compute_plddt_avg(json_path)
                    plddt_scores[file].append((input_dir, avg))
                except Exception as e:
                    print(f"Failed to process {json_path}: {e}")

    for filename, sources in plddt_scores.items():
        # Select the entry with max average plddt
        best_dir, best_score = max(sources, key=lambda x: x[1])
        base_name = os.path.splitext(filename)[0]

        # Copy all files with the same base name and any extension
        for file in os.listdir(best_dir):
            if file.startswith(base_name + '.'):
                src = os.path.join(best_dir, file)
                dst = os.path.join(output_dir, file)
                shutil.copy2(src, dst)
                print(f"Copied {file} from {best_dir} to {output_dir}")

if __name__ == '__main__':
    main()

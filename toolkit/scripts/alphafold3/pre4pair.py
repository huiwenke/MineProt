import argparse
import os
import json
import itertools

def main():
    parser = argparse.ArgumentParser(description='Generate paired JSON configurations.')
    parser.add_argument('-i', '--input', nargs='+', required=True, help='Input directories (at least two)')
    parser.add_argument('-o', '--output', required=True, help='Output directory')
    args = parser.parse_args()

    input_dirs = args.input
    output_dir = args.output

    if len(input_dirs) < 2:
        parser.error("At least two input directories are required.")

    first_input = input_dirs[0]
    other_inputs = input_dirs[1:]

    # Iterate over each subdirectory in the first input directory
    for dir_name in os.listdir(first_input):
        dir_path = os.path.join(first_input, dir_name)
        if not os.path.isdir(dir_path):
            continue

        # Construct the expected JSON filename (dir_name_data.json)
        json_filename = f"{dir_name}_data.json"
        
        # Check if all input directories have this JSON file
        valid = True
        for input_dir in input_dirs:
            json_path = os.path.join(input_dir, dir_name, json_filename)
            if not os.path.isfile(json_path):
                valid = False
                break
        if not valid:
            print(f"Skipping {dir_name}: missing {json_filename} in some inputs")
            continue

        # Read sequences from all input JSON files
        sequences_list = []
        for input_dir in input_dirs:
            json_path = os.path.join(input_dir, dir_name, json_filename)
            with open(json_path, 'r') as f:
                data = json.load(f)
                sequences = data.get('sequences', [])
                sequences_list.append(sequences)

        # Check if all sequences have the same length
        seq_lengths = [len(seq) for seq in sequences_list]
        if len(set(seq_lengths)) != 1:
            print(f"Skipping {dir_name}: varying sequence lengths")
            continue
        seq_length = seq_lengths[0]

        # Generate all possible combinations (excluding uniform choices)
        num_inputs = len(input_dirs)
        all_combos = itertools.product(range(num_inputs), repeat=seq_length)
        valid_combos = [combo for combo in all_combos if len(set(combo)) > 1]
        valid_combos_sorted = sorted(valid_combos)

        # Load base JSON from the first input
        base_path = os.path.join(input_dirs[0], dir_name, json_filename)
        with open(base_path, 'r') as f:
            base_json = json.load(f)
        base_json['sequences'] = []  # Clear original sequences

        # Generate and save each paired configuration
        for idx, combo in enumerate(valid_combos_sorted, 1):
            new_sequences = []
            for pos in range(seq_length):
                src_idx = combo[pos]
                new_sequences.append(sequences_list[src_idx][pos])
            
            temp_json = base_json.copy()
            temp_json['sequences'] = new_sequences

            paired_dir = os.path.join(output_dir, f'paired-{idx}')
            os.makedirs(paired_dir, exist_ok=True)
            output_path = os.path.join(paired_dir, json_filename)
            
            with open(output_path, 'w') as f_out:
                json.dump(temp_json, f_out, indent=2)
            print(f"Generated {output_path}")

if __name__ == '__main__':
    main()
import os
import argparse
import shutil
import random

def main():
    parser = argparse.ArgumentParser(description="Distribute files into multiple directories.")
    parser.add_argument("-i", "--input", type=str, default=".", help="Source directory (default: current directory)")
    parser.add_argument("-o", "--output", type=str, default=".", help="Target directory (default: current directory)")
    parser.add_argument("-n", "--number", type=int, default=1, help="Number of bins to distribute files into (default: 1)")
    parser.add_argument("--file", type=str, required=True, help="File type to distribute (e.g., '.a3m')")

    args = parser.parse_args()
    source_dir = args.input
    target_dir = args.output
    num_bins = args.number
    file_type = args.file

    # Validate input directory
    if not os.path.isdir(source_dir):
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return

    # Create target directories
    for i in range(num_bins):
        os.makedirs(os.path.join(target_dir, str(i)), exist_ok=True)

    # Gather files
    files = [f for f in os.listdir(source_dir) if f.endswith(file_type)]
    file_count = len(files)

    if file_count == 0:
        print(f"No files of type '{file_type}' found in source directory '{source_dir}'.")
        return

    # Shuffle files
    random.shuffle(files)

    # Calculate distribution parameters
    average = file_count // num_bins
    extra = file_count % num_bins

    # Distribute files
    for index, file in enumerate(files):
        if index < (average + 1) * extra:
            folder = index // (average + 1)
        else:
            folder = extra + (index - (average + 1) * extra) // average

        target_path = os.path.join(target_dir, str(folder))
        source_path = os.path.join(source_dir, file)

        if os.path.isfile(source_path):
            shutil.copy(source_path, target_path)
        else:
            print(f"Warning: File '{file}' not found.")

    print(f"Distribution complete. Total files: {file_count}")

if __name__ == "__main__":
    main()

import hashlib
import json
import os
import random
import shutil
import string
import time
from pathlib import Path


def random_string(num):
    """
    Generate a random string.
    :param num: Seed number, should be 0 or positive, int
    :return: MD5 encoded random string, str
    """
    salt = "".join(random.sample(string.ascii_letters + string.digits, num)) + str(time.time())
    return hashlib.md5(salt.encode("utf-8")).hexdigest()


def rename_model(name_mode, file_name, input_dir):
    """
    Rename files and move them to output directory.
    :param name_mode: Renaming mode, int
    :param file_name: Original file name, str
    :param input_dir: Path to input directory, str
    :return: New file name, str
    """
    input_path = os.path.join(input_dir, file_name)
    prefix = os.path.splitext(file_name)[0]
    if name_mode == 0:
        # 0: Use prefix
        new_prefix = prefix
    elif name_mode == 1:
        # 1: Use name in .a3m
        with open(input_path, "r") as f:
            new_prefix = next(line for line in f if line.startswith(">"))[1:].split()[0]
    elif name_mode == 2:
        # 2: Auto rename
        new_prefix = "MP_" + random_string(10)
    else:
        # 3: Customize name with user input
        print("Please enter a name:")
        new_prefix = input()
    return new_prefix


def move_predictions(staged, destination, name_mode):
    """Choose one name per model so structure, scores and MSA stay together."""
    staged = Path(staged)
    destination = Path(destination)
    names = []
    for structure in sorted(staged.glob("*.pdb")):
        msa = structure.with_suffix(".a3m")
        if name_mode == 1 and not msa.is_file():
            raise ValueError(f"Naming mode 1 requires an A3M file for {structure.stem}")
        name = rename_model(name_mode, msa.name, str(staged))
        if not name or name in (".", "..") or any(c in name for c in ("/", "\\", "\x00")):
            raise ValueError(f"Invalid model name: {name!r}")
        if name in names:
            raise ValueError(f"Multiple predictions map to the same name: {name}")
        names.append(name)
        for suffix in (".a3m", ".json", ".pdb"):
            source = structure.with_suffix(suffix)
            if not source.is_file():
                continue
            if source.suffix == ".json":
                data = json.loads(source.read_text())
                if "pae" in data:
                    data["pae"] = [[round(value) for value in row] for row in data["pae"]]
                source.write_text(json.dumps(data, separators=(",", ":")))
            shutil.move(str(source), destination / (name + source.suffix))
    return names

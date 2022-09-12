import time
import hashlib
import random
import string
import os

def RandomStr(num):
    """
    Generate a random string.
    :param num: Seed number, should be 0 or positive, int
    :return: MD5 encoded random string, str
    """
    salt = ''.join(random.sample(string.ascii_letters+string.digits, num))+str(time.time())
    return hashlib.md5(salt.encode("utf-8")).hexdigest()

def ReName(name_mode, file_name, input_dir):
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
        with open(input_path, 'r') as f:
            new_prefix = f.readlines()[1][1:-1].split(' ')[0]
    elif name_mode == 2:
        # 2: Auto rename
        new_prefix = "MP_" + RandomStr(10)
    else:
        # 3: Customize name with user input
        print("Please enter a name:")
        new_prefix = input()
    return new_prefix
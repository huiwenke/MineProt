import time
import hashlib
import random
import string

def RandomStr(num):
    """
    Generate a random string.
    :param num: Seed number, should be 0 or positive, int
    :return: MD5 encoded random string, str
    """
    salt = ''.join(random.sample(string.ascii_letters+string.digits, num))+str(time.time())
    return hashlib.md5(salt.encode("utf-8")).hexdigest()
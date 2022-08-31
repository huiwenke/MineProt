import time
import hashlib
import random
import string

def RandomStr(num):
    salt = ''.join(random.sample(string.ascii_letters+string.digits, num))+str(time.time())
    return hashlib.md5(salt.encode("utf-8")).hexdigest()
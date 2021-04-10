from . import os

import json
from Crypto.Cipher import AES
import hashlib


def save(exchange, password, **kwargs):
    if os.path.exists('Settings'):
        data = load(password)
        if not data:
            return False
    else:
        data = {'key': password}

    with open('Settings', 'wb') as sf:
        hkey = hashlib.sha256(password.encode()).digest()
        aes = AES.new(hkey, AES.MODE_EAX, hkey)
        ec = exchange.lower()
        data[ec] = {}
        data[ec].update(kwargs)

        jdata = json.dumps(data)
        enc = aes.encrypt(jdata.encode())

        sf.write(enc)
    return True


def load(password):
    if not os.path.exists('Settings'):
        return {}
    with open('Settings', 'rb') as sf:
        edata = sf.read()
        hkey = hashlib.sha256(password.encode()).digest()
        aes = AES.new(hkey, AES.MODE_EAX, hkey)
        jdata = aes.decrypt(edata)
        try:
            data = json.loads(jdata.decode())
        except:
            return False

    return data
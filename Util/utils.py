import configparser
import requests

from Exchanges.upbit.upbit import BaseUpbit
from Exchanges.binance.binance import Binance
from Exchanges.bithumb.bithumb import BaseBithumb
from DiffTrader.GlobalSetting.settings import SaiUrls

from Util.pyinstaller_patch import debugger

import redis
import json


cfg = configparser.ConfigParser()
cfg.read('../GlobalSetting/Settings.ini')


def get_redis(key):
    """
        key: str
    """
    try:
        rd = redis.StrictRedis(host='localhost', port=6379, db=0)

        value = rd.get(key)

        if not value:
            return None

        json_to_dict_value = json.loads(value)

        return json_to_dict_value
    except:
        return None


def set_redis(key, value):
    """
        key: str
        value: dict
    """
    rd = redis.StrictRedis(host='localhost', port=6379, db=0)

    dict_to_json_value = json.dumps(value)

    rd.set(key, dict_to_json_value)

    return


def get_exchanges():
    obj = dict()
    if cfg['Upbit']['Run'] == 'True':
        obj['Upbit'] = BaseUpbit(cfg['Upbit']['Key'], cfg['Upbit']['Secret'])
    if cfg['Binance']['Run'] == 'True':
        obj['Binance'] = Binance(cfg['Binance']['Key'], cfg['Binance']['Secret'])
    if cfg['Bithumb']['Run'] == 'True':
        obj['Bithumb'] = BaseBithumb(cfg['Bithumb']['Key'], cfg['Bithumb']['Secret'])

    return obj


def get_auto_withdrawal():
    return True if cfg['general']['auto withdrawal'].upper() == 'Y' else False


def send_to_sai_server(path, data):
    rq = requests.post(url=SaiUrls.BASE + path, json=json.dumps(data))
    result = rq.json()

    return result


class FunctionExecutor(object):
    def __init__(self, func):
        self._func = func
        self._success = False
        self._trace = list()

    def loop_executor(self, *args, **kwargs):
        self._trace.append('loop_executor')
        debugger.debug(
            'loop_executor, parameter={}, {}'.format(args, kwargs)
        )
        for _ in range(3):
            result = self._func(*args, **kwargs)

            if result.success:
                return result

        return result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        debugger.debug('Exit FunctionExecutor, trace: [{}]'.format(' -> '.format(self._trace)))
        return None

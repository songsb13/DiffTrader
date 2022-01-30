from Exchanges.upbit.upbit import BaseUpbit
from Exchanges.binance.binance import Binance
from Exchanges.bithumb.bithumb import BaseBithumb

from Util.pyinstaller_patch import debugger

from DiffTrader.GlobalSetting.settings import ServerInformation

from decimal import Decimal
import redis
import json
import time
import configparser


cfg = configparser.ConfigParser()
cfg.read('../GlobalSetting/Settings.ini')
rd = redis.StrictRedis(**ServerInformation.REDIS)


def publish_redis(key, value):
    """
        key: str
        value: dict
    """
    dict_to_json_value = json.dumps(value)

    rd.publish(key, dict_to_json_value)


def subscribe_redis(key):
    """
        (n-1)+(n-2) ... +1
    """
    ps = rd.pubsub()

    ps.subscribe(key)
    return ps


def get_redis(key):
    """
        key: str
    """
    try:
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


def get_min_profit():
    return Decimal(cfg['Profit']['Withdrawal Percent']).quantize(Decimal(10) ** -6)


class FunctionExecutor(object):
    def __init__(self, func, sleep_time=0):
        self._func = func
        self._success = False
        self._trace = list()
        self._sleep_time = sleep_time

    def loop_executor(self, *args, **kwargs):
        self._trace.append('loop_executor')
        debugger.debug(
            'loop_executor, parameter={}, {}'.format(args, kwargs)
        )
        for _ in range(3):
            result = self._func(*args, **kwargs)

            if result.success:
                return result
            time.sleep(self._sleep_time)
        return result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        debugger.debug('Exit FunctionExecutor, trace: [{}]'.format(' -> '.format(self._trace)))
        return None

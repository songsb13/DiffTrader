from Exchanges.upbit.upbit import BaseUpbit
from Exchanges.binance.binance import Binance
from Exchanges.bithumb.bithumb import BaseBithumb
from DiffTrader.GlobalSetting.settings import REDIS_SERVER, CONFIG

from Util.pyinstaller_patch import debugger

from decimal import Decimal
import json
import time


def publish_redis(key, value):
    """
        key: str
        value: dict
    """
    dict_to_json_value = json.dumps(value)

    REDIS_SERVER.publish(key, dict_to_json_value)


def subscribe_redis(key):
    """
        (n-1)+(n-2) ... +1
    """
    ps = REDIS_SERVER.pubsub()

    ps.subscribe(key)
    return ps


def get_redis(key):
    """
        key: str
    """
    try:
        value = REDIS_SERVER.get(key)

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

    REDIS_SERVER.set(key, dict_to_json_value)

    return


def get_exchanges():
    obj = dict()
    if CONFIG['Upbit']['Run'] == 'True':
        obj['Upbit'] = BaseUpbit(CONFIG['Upbit']['Key'], CONFIG['Upbit']['Secret'])
    if CONFIG['Binance']['Run'] == 'True':
        obj['Binance'] = Binance(CONFIG['Binance']['Key'], CONFIG['Binance']['Secret'])
    if CONFIG['Bithumb']['Run'] == 'True':
        obj['Bithumb'] = BaseBithumb(CONFIG['Bithumb']['Key'], CONFIG['Bithumb']['Secret'])

    return obj


def get_auto_withdrawal():
    return True if CONFIG['general']['auto withdrawal'].upper() == 'Y' else False


def get_min_profit():
    return Decimal(CONFIG['Profit']['Withdrawal Percent']).quantize(Decimal(10) ** -6)


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

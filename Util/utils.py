import configparser

from Exchanges.upbit.upbit import BaseUpbit
from Exchanges.binance.binance import Binance
from Exchanges.bithumb.bithumb import BaseBithumb

from Util.pyinstaller_patch import *


def get_exchanges():
    cfg = configparser.ConfigParser()
    cfg.read('../GlobalSetting/Settings.ini')

    obj = dict()
    if cfg['Upbit']['Run'] == 'True':
        obj['Upbit'] = BaseUpbit(cfg['Upbit']['Key'], cfg['Upbit']['Secret'])
    if cfg['Binance']['Run'] == 'True':
        obj['Binance'] = Binance(cfg['Binance']['Key'], cfg['Binance']['Secret'])
    if cfg['Bithumb']['Run'] == 'True':
        obj['Bithumb'] = BaseBithumb(cfg['Bithumb']['Key'], cfg['Bithumb']['Secret'])

    return obj


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

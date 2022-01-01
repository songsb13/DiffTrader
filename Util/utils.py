import configparser

from Exchanges.upbit.upbit import BaseUpbit
from Exchanges.binance.binance import Binance
from Exchanges.bithumb.bithumb import BaseBithumb


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

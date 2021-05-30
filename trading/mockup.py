import unittest
from unittest.mock import MagicMock, Mock


def profit_table_mock():
    """
    trade_date,
    symbol,
    primary_exchange,
    secondary_exchange,
    profit_btc,
    profit_percent
    """
    return [[1622354947, 'BTC_XRP', 'binance', 'bithumb', 0.001, 0.1],
            [1622350000, 'BTC_ETH', 'upbit', 'bithumb', 0.005, 0.2],
            [1622340000, 'BTC_EOS', 'upbit', 'binance', 0.007, 0.3]]


def profit_setting_mock():
    return {
        'min_profit_percent': 0.03,
        'min_profit_btc': 0.0075,
        'is_withdraw': False
    }

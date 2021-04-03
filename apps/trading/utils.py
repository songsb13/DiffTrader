"""
    trade_thread.py에서 사용되는 함수 집합체.
    todo 경로에 대해서 의논 필요함
"""

from decimal import Decimal
from settings import TAG_COINS, SAI_URL

import requests


def calculate_withdraw_amount(amount_of_coin, tx_fee):
    """
        :param amount_of_coin: amount of coin, BTC and ALT.
        :param tx_fee: transaction fee from exchanges.
        :return: send amount include the transaction fee.
    """
    return amount_of_coin + Decimal(tx_fee).quantize(
        Decimal(10) ** amount_of_coin.as_tuple().exponent)


def send_expected_profit(profit_object):
    """
    """
    res = requests.post(SAI_URL, data=profit_object.information)

    return True if res.status_code == 200 else False


def check_deposit_addrs(coin, deposit_dic):
    has_deposit = deposit_dic.get(coin, None)
    has_tag_deposit = deposit_dic.get(coin + 'TAG', None) if coin in TAG_COINS else None

    return all([has_deposit, has_tag_deposit])


def loop_wrapper(debugger):
    """
        wrapper that try loop up to 3 times
        It is used when defining variable information, fee, deposits, compare_orderbook and etc.
    """
    def _except_wrapper(func):
        def _wrap_func(self, *args):
            for _ in range(3):
                data = func(self, *args)
                if data is not None:
                    return data
                else:
                    debugger.debug(
                        'function [{}] is failed to setting a function.'.format(func.__name__))
                    time.sleep(5)
            else:
                debugger.debug('function [{}] is failed to setting a function, please try later.'.format(func.__name__))
                raise
        return _wrap_func
    return _except_wrapper

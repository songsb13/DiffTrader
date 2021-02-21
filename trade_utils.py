"""
    trade_thread.py에서 사용되는 함수 집합체.
    todo 경로에 대해서 의논 필요함
"""

from decimal import Decimal
from settings.defaults import TAG_COINS, SAI_URL

import requests


def send_amount_calculator(amount_of_coin, tx_fee):
    """
        :param amount_of_coin: amount of coin, BTC and ALT.
        :param tx_fee: transaction fee from exchanges.
        :return: send amount include the transaction fee.
    """
    return amount_of_coin + Decimal(tx_fee).quantize(
        Decimal(10) ** amount_of_coin.as_tuple().exponent)


def expect_profit_sender(profit_object):
    """
    """
    res = requests.post(SAI_URL, data=profit_object.information)

    return True if res.status_code == 200 else False


def is_exists_deposit_addrs(coin, deposit_dic):
    has_deposit = deposit_dic.get(coin, None)
    has_tag_deposit = deposit_dic.get(coin + 'TAG', None) if coin in TAG_COINS else None
    
    return all([has_deposit, has_tag_deposit])

from Exchanges.upbit.upbit import BaseUpbit
from Exchanges.binance.binance import Binance
from Exchanges.bithumb.bithumb import BaseBithumb
from DiffTrader.Util.utils import get_exchanges


class Trading(object):
    """
        monitoring process에서 넘어온 각종 이벤트 값들에 대한 트레이딩 시도
    """
    def __init__(self):
        pass

    def _trade(self, from_object, to_object, profit_information):
        """
            from_object: A object that will be buying the ALT coin
            to_object: A object that will be selling the ALT coin
            profit_information: information of profit
        """

        if profit_information['']:
            pass

    def trading(self):
        exchange_dict = get_exchanges()


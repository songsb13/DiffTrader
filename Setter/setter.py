from DiffTrader.Util.utils import get_exchanges, publish_redis
from DiffTrader.GlobalSetting.messages import SetterMessage as Msg
from Util.pyinstaller_patch import debugger

from multiprocessing import Process

import time
import asyncio


class Setter(Process):
    def __init__(self, user, exchange_str):
        debugger.debug(Msg.START(user, exchange_str))
        super(Setter, self).__init__()

        self._user = user
        self._exchange_str = exchange_str

        self._exchange = None

    def run(self) -> None:
        exchanges = get_exchanges()
        self._exchange = exchanges[self._exchange_str]
        now_time = time.time()
        lazy_data = dict()

        one_time_data = self._get_one_time_fresh_data()
        while True:
            if not lazy_data or (now_time + 3000) <= time.time():
                lazy_data = self._get_lazy_refresh_data()

            quick_data = self._get_quick_refresh_data()

            total_data = {
                **quick_data,
                **lazy_data,
                **one_time_data
            }

            publish_redis(self._exchange_str, total_data)
            time.sleep(10)

    def _get_quick_refresh_data(self):
        balance_result = self._exchange.get_balance()

        if not balance_result.success:
            debugger.debug(balance_result.message)
            return False

        dic = {
            'balance': balance_result.data,
        }

        return dic

    def _get_lazy_refresh_data(self):
        deposit_result = asyncio.run(self._exchange.get_deposit_addrs())
        if not deposit_result.success:
            debugger.debug(deposit_result.message)
            return False

        transaction_result = self._exchange.get_transaction_fee()
        if not transaction_result.success:
            debugger.debug(transaction_result.message)
            return False

        dic = {
            'deposit': deposit_result.data,
            'transaction_fee': transaction_result.data
        }

        return dic

    def _get_one_time_fresh_data(self):
        trading_result = self._exchange.get_trading_fee()
        if not trading_result.success:
            debugger.debug(trading_result.message)

        dic = {
            'trading_fee': trading_result.data
        }

        return dic

from DiffTrader.Util.utils import get_exchanges, publish_redis, task_wrapper
from DiffTrader.GlobalSetting.messages import SetterMessage as Msg
from DiffTrader.GlobalSetting.settings import DEFAULT_REFRESH_TIME, TEST_USER, DEBUG
from Util.pyinstaller_patch import debugger

from multiprocessing import Process

import time
import asyncio


class Setter(Process):
    def __init__(self, user, exchange_str):
        debugger.debug(Msg.START.format(user, exchange_str))
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
            if not lazy_data or (now_time + DEFAULT_REFRESH_TIME) <= time.time():
                lazy_data = self._get_lazy_refresh_data()

            quick_data = self._get_quick_refresh_data()

            total_data = {
                **quick_data,
                **lazy_data,
                **one_time_data
            }

            publish_redis(self._exchange_str, total_data, use_decimal=True)
            time.sleep(10)

    def _get_quick_refresh_data(self):
        # balance
        balance_result = self._exchange.get_balance()

        if not balance_result.success:
            debugger.debug(balance_result.message)
            return dict()

        dic = {
            'balance': balance_result.data,
        }

        return dic

    def _get_lazy_refresh_data(self):
        task_list = [
            {'fn': self._exchange.get_deposit_addrs},
            {'fn': self._exchange.get_transaction_fee}
        ]

        # deposits, transaction_fees
        deposit_result, transaction_result = asyncio.run(task_wrapper(task_list))
        if not deposit_result.success:
            debugger.debug(deposit_result.message)
            return dict()

        if not transaction_result.success:
            debugger.debug(transaction_result.message)
            return dict()

        dic = {
            'deposit': deposit_result.data,
            'transaction_fee': transaction_result.data
        }

        return dic

    def _get_one_time_fresh_data(self):
        # trading_fee, fee_count
        trading_result = self._exchange.get_trading_fee()
        trading_fee_count = self._exchange.fee_count()
        if not trading_result.success:
            debugger.debug(trading_result.message)

        dic = {
            'trading_fee': trading_result.data,
            'fee_count': trading_fee_count
        }

        return dic


if __name__ == '__main__':
    from DiffTrader.Util.utils import get_exchanges
    st = Setter(TEST_USER, 'Binance')
    st.run()

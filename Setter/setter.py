from DiffTrader.Util.utils import (
    DecimalDecoder,
    publish_redis,
    task_wrapper,
    subscribe_redis
)
from DiffTrader.GlobalSetting.messages import SetterMessage as Msg
from DiffTrader.GlobalSetting.settings import TraderConsts, TEST_USER, RedisKey, APIPriority
from Util.pyinstaller_patch import debugger
from multiprocessing import Process

import time
import asyncio
import json


class Setter(Process):
    publish_functions = ['get_balance', 'get_deposit_addrs', 'get_transaction_fee']

    def __init__(self, user, exchange_str):
        debugger.debug(Msg.START.format(user, exchange_str))
        super(Setter, self).__init__()

        self._user = user
        self._exchange_str = exchange_str

        self._exchange = None

    def run(self) -> None:
        exchanges = get_exchanges()
        set_quick, set_lazy = False, False
        self._exchange = exchanges[self._exchange_str]
        now_time = time.time()
        lazy_data, quick_data = dict(), dict()
        api_subscriber = subscribe_redis(RedisKey.UpbitAPISubRedisKey)

        one_time_data = self._get_one_time_fresh_data()
        while True:
            if (not lazy_data or (now_time + TraderConsts.DEFAULT_REFRESH_TIME) <= time.time()) and \
                    not set_lazy:
                self._pub('get_deposit_addrs')
                self._pub('get_transaction_fee')
                set_lazy = True

            if not set_quick:
                self._pub('get_balance')
                set_quick = True

            api_contents = api_subscriber.get_message()

            if api_contents:
                api_data = api_contents.get('data', 1)
                if isinstance(api_data, int):
                    time.sleep(1)
                    continue
                api_data = json.loads(api_data, cls=DecimalDecoder)
                if not api_data:
                    time.sleep(1)
                    continue
                elif api_data not in self.publish_functions:
                    time.sleep(1)
                    continue

            total_data = {
                **quick_data,
                **lazy_data,
                **one_time_data
            }

            publish_redis(self._exchange_str, total_data, use_decimal=True)
            set_quick, set_lazy = False
            time.sleep(10)

    def _pub(self, name):
        publish_redis(RedisKey.UpbitAPIPubRedisKey, {
            'name': name,
            'args': [],
            'kwargs': {},
            'priority': APIPriority.SEARCH,
        })

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
    st = Setter(TEST_USER, 'Upbit')
    st.run()

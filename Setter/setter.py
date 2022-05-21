from DiffTrader.Util.utils import (
    publish_redis,
    subscribe_redis
)
from DiffTrader.Util.logger import SetLogger
from DiffTrader.GlobalSetting.messages import SetterMessage as Msg
from DiffTrader.GlobalSetting.settings import TraderConsts, TEST_USER
from DiffTrader.GlobalSetting.objects import BaseProcess
from DiffTrader.GlobalSetting.settings import RedisKey
from Util.pyinstaller_patch import debugger

import time
import logging.config

setter_logger = SetLogger('setter', logging)
setter_logger = setter_logger.get_logger()
setter_logger.getLogger('setter')


class LogTest(object):
    def logt(self):
        setter_logger.debug('s-test1')
        setter_logger.info('s-test-2')


class Setter(BaseProcess):
    receive_type = 'common'
    require_functions = ['get_balance', 'get_deposit_addrs', 'get_transaction_fee']

    def __init__(self, user, exchange_str):
        debugger.debug(Msg.START.format(user, exchange_str))
        super(Setter, self).__init__()
        self._pub_api_redis_key = RedisKey.ApiKey[exchange_str]['publish']
        self._sub_api_redis_key = RedisKey.ApiKey[exchange_str]['subscribe']

        self._user = user
        self._exchange_str = exchange_str

        self._exchange = None

    def run(self) -> None:
        exchanges = get_exchanges()
        set_quick, set_lazy = False, False
        self._exchange = exchanges[self._exchange_str]
        api_subscriber = subscribe_redis(self._sub_api_redis_key)

        total_data = {**self._get_one_time_fresh_data()}
        init_update = set()
        while True:
            if not set_lazy:
                self.publish_redis_to_api_process('get_deposit_addrs', self._pub_api_redis_key, is_async=True, is_lazy=True)
                self.publish_redis_to_api_process('get_transaction_fee', self._pub_api_redis_key, is_async=True, is_lazy=True)
                set_lazy = True

            if not set_quick:
                self.publish_redis_to_api_process('get_balance', self._pub_api_redis_key)
                set_quick = True

            result = self.get_subscriber_api_contents(api_subscriber)

            if result is None:
                continue

            total_message = []
            for key in result.keys():
                if result[key]['success']:
                    total_data.update(result[key]['data'])
                    init_update.add(key)
                else:
                    total_message.append(result[key]['message'])

            if not init_update == self.require_functions:
                time.sleep(1)
                continue

            publish_redis(self._exchange_str, total_data, use_decimal=True)
            set_quick, set_lazy = False, False
            time.sleep(10)

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

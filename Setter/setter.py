from DiffTrader.Util.utils import (
    publish_redis,
    subscribe_redis
)
from DiffTrader.Util.logger import SetLogger
from DiffTrader.GlobalSetting.messages import CommonMessage as CMsg
from DiffTrader.GlobalSetting.settings import TEST_USER
from DiffTrader.GlobalSetting.objects import MessageControlMixin
from DiffTrader.GlobalSetting.settings import RedisKey


import time
import logging.config


__file__ = 'setter.py'


logging_config = SetLogger.get_config_base_process(__file__)
logging.config.dictConfig(logging_config)


class Setter(MessageControlMixin):
    receive_type = 'common'
    require_functions = ['get_balance', 'get_deposit_addrs', 'get_transaction_fee']

    name, name_kor = 'Setter', '데이터 세터'

    def __init__(self, user, exchange_str):
        logging.info(CMsg.START)
        super(Setter, self).__init__()
        self._pub_api_redis_key = RedisKey.ApiKey[exchange_str]['publish']
        self._sub_api_redis_key = RedisKey.ApiKey[exchange_str]['subscribe']

        self._user = user
        self._exchange_str = exchange_str

        self._exchange = None

    def run(self) -> None:
        logging.debug(CMsg.ENTRANCE)
        exchanges = get_exchanges()
        set_quick, set_lazy = False, False
        self._exchange = exchanges[self._exchange_str]
        api_subscriber = subscribe_redis(self._sub_api_redis_key)

        total_data = {**self._get_one_time_fresh_data()}
        init_update = set()
        while True:
            if not set_lazy:
                self.publish_redis_to_api_process('get_deposit_addrs', self._pub_api_redis_key, logging=logging,
                                                  is_async=True, is_lazy=True)
                self.publish_redis_to_api_process('get_transaction_fee', self._pub_api_redis_key, logging=logging,
                                                  is_async=True, is_lazy=True)
                set_lazy = True

            if not set_quick:
                self.publish_redis_to_api_process('get_balance', self._pub_api_redis_key)
                set_quick = True

            success, result = self.get_subscribe_result(api_subscriber)

            if not success:
                logging.warning(result)
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

            publish_redis(self._exchange_str, total_data, use_decimal=True, logging=logging)
            set_quick, set_lazy = False, False
            time.sleep(1)

    def _get_one_time_fresh_data(self):
        # trading_fee, fee_count
        trading_result = self._exchange.get_trading_fee()
        trading_fee_count = self._exchange.fee_count()
        if not trading_result.success:
            logging.debug(trading_result.message)

        dic = {
            'trading_fee': trading_result.data,
            'fee_count': trading_fee_count
        }

        return dic


if __name__ == '__main__':
    from DiffTrader.Util.utils import get_exchanges
    st = Setter(TEST_USER, 'Upbit')
    st.run()

"""
    목적
        1. 각 거래소의 balance, transaction fee, deposit address 등 거래에 필요한 정보를 가져온다.

    기타
        1. 발생하는 Process의 수는 거래소의 수이다.
        2. 각 Process들은 각 api_process와 통신하며, 거래에 필요한 데이터들을 요청한다.
        3. 결과 값은 monitoring process로 publish된다.
"""
from DiffTrader.utils.util import subscribe_redis, publish_redis, get_exchange_by_name, MessageControlMixin
from DiffTrader.settings.base import RedisKey, DEBUG, SetLogger
from DiffTrader.settings.message import CommonMessage as CMsg

import time
import logging.config


__file__ = "setter.py"

logging_config = SetLogger.get_config_base_process(__file__)
logging.config.dictConfig(logging_config)


class Setter(MessageControlMixin):
    require_functions = {"get_balance", "get_deposit_addrs", "get_transaction_fee"}

    def __init__(self, exchange_str):
        super(Setter, self).__init__()
        logging.info(CMsg.START)

        exchange_str = exchange_str.lower()

        self._pub_api_redis_key = RedisKey.ApiKey[exchange_str]["publish"]
        self._sub_api_redis_key = RedisKey.ApiKey[exchange_str]["subscribe"]

        self._exchange_str = exchange_str

        self._exchange = None
        self._live_check = time.time() + 60

    def run(self) -> None:
        logging.debug(CMsg.ENTRANCE)
        self._exchange = get_exchange_by_name(self._exchange_str)
        api_subscriber = subscribe_redis(self._sub_api_redis_key)

        total_data = {**self._get_one_time_fresh_data()}
        init_update = set()
        while True:
            if time.time() >= self._live_check:
                self._live_check = time.time() + 60
                logging.debug(f"live check in setter, {self._exchange_str}")

            self.publish_redis_to_api_process(
                "get_deposit_addrs",
                self._pub_api_redis_key,
                logging=logging,
                is_async=True,
                is_lazy=True,
            )
            self.publish_redis_to_api_process(
                "get_transaction_fee",
                self._pub_api_redis_key,
                logging=logging,
                is_async=True,
                is_lazy=True,
            )
            self.publish_redis_to_api_process(
                "get_balance", self._pub_api_redis_key, logging=logging,
            )

            result = self.get_subscribe_result(api_subscriber)

            if not result.success:
                logging.warning(result.message)
                continue

            total_message = []
            for key in result.data.keys():
                if result.data[key]["success"]:
                    total_data[key] = result.data[key]["data"]
                    init_update.add(key)
                else:
                    total_message[key] = result.data[key]["message"]

            if not init_update == self.require_functions:
                time.sleep(1)
                continue

            # if DEBUG:
            #     logging.info(total_data)

            publish_redis(
                self._exchange_str, total_data, use_decimal=True, logging=logging
            )
            time.sleep(1)

    def _get_one_time_fresh_data(self):
        # trading_fee, fee_count
        trading_result = self._exchange.get_trading_fee()
        trading_fee_count = self._exchange.fee_count()
        if not trading_result.success:
            logging.debug(trading_result.message)

        dic = {"trading_fee": trading_result.data, "fee_count": trading_fee_count}

        return dic


if __name__ == "__main__":
    import sys
    try:
        filename, _exchange_str, *_ = sys.argv
        logging.debug(f"{filename=}, {_exchange_str=}")
        Setter(_exchange_str).run()

    except Exception as ex:
        logging.exception("FATAL")
        print('PROGRAMCLOSED', ex)

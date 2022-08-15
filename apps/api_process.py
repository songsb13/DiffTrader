"""
    이 파일은 거래소의 api를 관리하는 API process가 정의된 object가 있음.
    This file has API process object that managing exchange's API
"""


from multiprocessing import Process
import time
import asyncio
import json

from DiffTrader.settings.base import APIPriority, TraderConsts, RedisKey, SetLogger
from DiffTrader.utils.util import (
    get_exchanges,
    subscribe_redis,
    publish_redis,
    DecimalDecoder,
)

import logging.config


__file__ = "api_process.py"


logging_config = SetLogger.get_config_base_process(__file__)
logging.config.dictConfig(logging_config)


class BaseAPIProcess(Process):
    pub_api_redis_key = ""
    sub_api_redis_key = ""

    def __init__(self, exchange_str):
        super(BaseAPIProcess, self).__init__()
        self._exchange_str = exchange_str
        self._wait_time = 10
        self.__api_container = self.__set_api_container()
        logging.info("api_process를 실행합니다.")

    def __set_api_container(self):
        return [[] for _ in range(APIPriority.LENGTH)]

    def __set_after_time(self):
        return self.__get_seconds() + self._wait_time

    def __get_seconds(self):
        return int(time.time())

    def run(self) -> None:
        exchanges = get_exchanges()
        exchange = exchanges[self._exchange_str]
        _api_subscriber = subscribe_redis(self.pub_api_redis_key)

        after_time = self.__get_seconds() + self._wait_time
        refresh_time = self.__get_seconds() + TraderConsts.DEFAULT_REFRESH_TIME
        lazy_cache = dict()
        on_waiting = set()
        while True:
            """
            결과 값을 전체 도메인에 broadcast하고, 결과 값 function_name 통해 각 도메인에서 데이터 판단을 진행한다.
            현재 사용 도메인: setter, withdrawal
            """
            message = _api_subscriber.get_message()
            if message:
                info = message.get("data", 1)
            else:
                info = message
            if info and not isinstance(info, int):
                info = json.loads(info, cls=DecimalDecoder)
                if info["fn_name"] in on_waiting:
                    print('onwaiting_function', info["fn_name"])
                    continue

                if (
                    time.time() <= refresh_time
                    and info["is_lazy"]
                    and info["fn_name"] in lazy_cache
                ):
                    refresh_time = time.time() + TraderConsts.DEFAULT_REFRESH_TIME
                    print('lazy-data', info["fn_name"])
                    publish_redis(
                        self.sub_api_redis_key,
                        lazy_cache[info["fn_name"]],
                        use_decimal=True
                    )
                else:
                    function_ = getattr(exchange, info["fn_name"])
                    on_waiting.add(info["fn_name"])
                    self.__api_container[int(info["priority"])].append(
                        (function_, info)
                    )
            if self.__get_seconds() < after_time:
                time.sleep(1)
                continue
            for container in self.__api_container:
                if not container:
                    continue
                for fn, container_info in container:
                    # corutine에 대한 처리 필요함.
                    for _ in range(2):
                        try:
                            result = (
                                asyncio.run(
                                    fn(
                                        *container_info["args"],
                                        **container_info["kwargs"]
                                    )
                                )
                                if asyncio.iscoroutinefunction(fn)
                                else fn(
                                    *container_info["args"], **container_info["kwargs"]
                                )
                            )
                            break
                        except RuntimeError as e:
                            if str(e) != "Event loop is closed":
                                logging.error(e)
                                on_waiting.remove(info["fn_name"])
                                raise
                        time.sleep(1)
                    else:
                        on_waiting.remove(info["fn_name"])
                        raise
                    if not result.success:
                        logging.debug(result.message)

                    fn_result = {
                        "success": result.success,
                        "data": result.data,
                        "message": result.message,
                    }

                    data = {
                        container_info["fn_name"]: fn_result
                    }
                    on_waiting.remove(container_info["fn_name"])
                    lazy_cache.update(data)
                    publish_redis(self.sub_api_redis_key, data, use_decimal=True)
            else:
                self.__api_container = self.__set_api_container()
            after_time = self.__set_after_time()


class UpbitAPIProcess(BaseAPIProcess):
    pub_api_redis_key = RedisKey.ApiKey["upbit"]["publish"]
    sub_api_redis_key = RedisKey.ApiKey["upbit"]["subscribe"]

    def __init__(self):
        super(UpbitAPIProcess, self).__init__("upbit")


class BinanceAPIProcess(BaseAPIProcess):
    pub_api_redis_key = RedisKey.ApiKey["binance"]["publish"]
    sub_api_redis_key = RedisKey.ApiKey["binance"]["subscribe"]

    def __init__(self):
        super(BinanceAPIProcess, self).__init__("binance")


if __name__ == "__main__":
    import sys
    try:
        filename, exchange_str, *_ = sys.argv
        logging.debug(f"{filename=}, {exchange_str=}")
        if exchange_str == 'upbit':
            UpbitAPIProcess().run()
        elif exchange_str == 'binance':
            BinanceAPIProcess().run()
    except Exception as ex:
        print('PROGRAMCLOSED', ex)

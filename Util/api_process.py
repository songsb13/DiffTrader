"""
    이 파일은 거래소의 api를 관리하는 API process가 정의된 object가 있음.
    This file has API process object that managing exchange's API
"""


from multiprocessing import Process
import time
import json

from DiffTrader.GlobalSetting.settings import (
    APIPriority,
    TraderConsts,
    RedisKey
)
from DiffTrader.Util.utils import (
    get_exchanges,
    subscribe_redis,
    publish_redis,
    DecimalDecoder
)

from Util.pyinstaller_patch import debugger


class BaseAPIProcess(Process):
    pub_api_redis_key = ''
    sub_api_redis_key = ''

    def __init__(self, exchange_str):
        super(BaseAPIProcess, self).__init__()
        self._exchange_str = exchange_str
        self._wait_time = 3
        self._api_container = [[] for _ in range(APIPriority.LENGTH)]
        self._api_subscriber = subscribe_redis(self.pub_api_redis_key)

    def run(self) -> None:
        exchanges = get_exchanges()
        exchange = exchanges[self._exchange_str]

        after_time = time.time() + self._wait_time
        refresh_time = time.time() + TraderConsts.DEFAULT_REFRESH_TIME
        lazy_cache = {}
        while True:
            """
                결과 값을 전체 도메인에 broadcast하고, 결과 값 receive_type을 통해 각 도메인에서 데이터 판단을 진행한다.
                현재 사용 도메인: setter, withdrawal
            """
            message = self._api_subscriber.get_message()
            if message:
                info = message.get('data', 1)
            else:
                info = message
            if not info or isinstance(info, int):
                time.sleep(1)
                continue
            info = json.loads(info, cls=DecimalDecoder)
            if time.time() > refresh_time and info['is_lazy'] and info['fn_name'] in lazy_cache:
                refresh_time = time.time() + TraderConsts.DEFAULT_REFRESH_TIME
                publish_redis(self.sub_api_redis_key, lazy_cache[info['receive_type']][info['fn_name']])

            function_ = getattr(exchange, info['fn_name'])

            self._api_container[int(info['priority'])].append((function_, info['args'], info['kwargs']))
            if time.time() >= after_time:
                for container in self._api_container:
                    if not container:
                        continue
                    for fn, args, kwargs, *_ in container:
                        # corutine에 대한 처리 필요함.
                        result = fn(*args, **kwargs)
                        if not result.success:
                            debugger.debug(result.message)
                            # set log
                        data = {
                            info['receive_type']: {
                                info['fn_name']: {
                                    'success': result.success,
                                    'data': result.data,
                                    'message': result.message
                                }
                            }
                        }
                        lazy_cache.update(data)
                        publish_redis(self.sub_api_redis_key, data)
                after_time = time.time() + self._wait_time


class UpbitAPIProcess(BaseAPIProcess):
    pub_api_redis_key = RedisKey.ApiKey['Upbit']['publish']
    sub_api_redis_key = RedisKey.ApiKey['Upbit']['subscribe']

    def __init__(self):
        super(UpbitAPIProcess, self).__init__("Upbit")


class BinanceAPIProcess(BaseAPIProcess):
    pub_api_redis_key = RedisKey.ApiKey['Binance']['publish']
    sub_api_redis_key = RedisKey.ApiKey['Binance']['subscribe']

    def __init__(self):
        super(BinanceAPIProcess, self).__init__("Binance")


if __name__ == '__main__':
    ua = UpbitAPIProcess()
    ua.run()

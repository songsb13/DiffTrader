import time
import json

from multiprocessing import Process
from DiffTrader.GlobalSetting.settings import (
    APIPriority,
    TraderConsts
)
from DiffTrader.Util.utils import (
    get_exchanges,
    set_redis,
    publish_redis,
    get_redis,
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
        self._api_container = [set() for _ in range(APIPriority.LENGTH)]

    def run(self) -> None:
        exchanges = get_exchanges()
        exchange = exchanges[self._exchange_str]

        after_time = time.time() + self._wait_time
        refresh_time = time.time() + TraderConsts.DEFAULT_REFRESH_TIME
        lazy_cache = {}
        while True:
            """
            priority = api priority

            name: api function name
            args: api args
            kwargs: api kwargs
            get data from pub_api_redis_key and send to sub_api_redis_key
            2개의 함수 그룹
            async로 돌아가야할 그룹, sync한 그룹
            deposit_addrs랑 get_transaction_fee
            """
            info = get_redis(self.pub_api_redis_key)
            if not info:
                continue
            if not (time.time() <= refresh_time) and info['is_lazy'] and info['fn_name'] in lazy_cache:
                set_redis(self.sub_api_redis_key, lazy_cache[info['receive_type']][info['fn_name']])

            function_ = getattr(exchange, info['fn_name'])

            self._api_container[info['priority']].add((function_, info['args'], info['kwargs']))
            if time.time() >= after_time:
                for fn, args, kwargs, _ in self._api_container:
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
                    set_redis(self.sub_api_redis_key, data)


class BaseProcess(object):
    # base process for setter, monitoring and etc..
    pub_api_redis_key = ''
    sub_api_redis_key = ''
    receive_type = ''
    require_functions = []

    def unpacking_message(self, api_contents):
        if api_contents:
            raw_data = api_contents.get('data', 1)
            if isinstance(raw_data, int):
                return None

            to_json = json.loads(raw_data, cls=DecimalDecoder)
            if not to_json:
                return None

            data = to_json.get(self.receive_type, None)
            if data is None:
                return None

            result = {}
            for key in data.keys():
                if key not in self.require_functions:
                    continue
                result[key] = data[key]
            else:
                return result

    def pub_api_fn(self, fn_name, is_async=False, is_lazy=False, api_priority=APIPriority.SEARCH):
        publish_redis(self.pub_api_redis_key, {
            'is_async': is_async,
            'is_lazy': is_lazy,
            'receive_type': self.receive_type,
            'fn_name': fn_name,
            'args': [],
            'kwargs': {},
            'priority': api_priority,
        })

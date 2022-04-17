import time

from multiprocessing import Process
from DiffTrader.GlobalSetting.settings import (
    APIPriority
)
from DiffTrader.Util.utils import (
    get_exchanges,
    set_redis,
    get_redis
)

from Util.pyinstaller_patch import debugger


class BaseAPIProcess(Process):
    api_redis_key = ''

    def __init__(self, exchange_str):
        super(BaseAPIProcess, self).__init__()
        self._exchange_str = exchange_str
        self._wait_time = 3
        self._api_container = [set() for _ in range(APIPriority.LENGTH)]

    def run(self) -> None:
        exchanges = get_exchanges()
        exchange = exchanges[self._exchange_str]

        after_time = time.time() + self._wait_time
        while True:
            """
            priority = api priority

            name: api function name
            args: api args
            kwargs: api kwargs
            """
            info = get_redis(self.api_redis_key)

            if not info:
                continue

            function_ = getattr(exchange, info['name'])

            self._api_container[info['priority']].add((function_, info['args'], info['kwargs']))
            if time.time() >= after_time:
                sorted(self._api_container, key=lambda priority: priority[-1])
                for fn, args, kwargs, _ in self._api_container:
                    result = fn(*args, **kwargs)

                    if not result.success:
                        debugger.debug(result.message)
                        # set log
                    data = {
                        info['name']: {
                            'receive_type': info['receive_type'],
                            'success': result.success,
                            'data': result.data,
                            'message': result.message
                        }
                    }
                    set_redis(self.api_redis_key, data)



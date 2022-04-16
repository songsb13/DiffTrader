import json
import time

from multiprocessing import Process
from DiffTrader.GlobalSetting.settings import (
    TraderConsts,
    RedisKey,
    DEBUG,
    TEST_USER
)
from DiffTrader.Util.utils import (
    get_exchanges,
    subscribe_redis,
    get_min_profit,
    set_redis,
    DecimalDecoder,
    task_wrapper,
    get_redis
)

from Util.pyinstaller_patch import debugger


class BaseAPIProcess(Process):
    """
        기본적으로 BaseAPIProcess 실행,
        별도의 로직이 필요한경우
        ExchangeAPIProcess로 명명하고 override
    """
    def __init__(self, exchange_str):
        super(BaseAPIProcess, self).__init__()
        self._exchange_str = exchange_str
        self._wait_time = 3
        self._api_container = set()

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
            dest_key: destination redis key
            type_: sync, async
            
            """
            info = get_redis(RedisKey.APIInformation)

            if not info:
                continue

            function_ = getattr(exchange, info['name'])

            self._api_container.add((function_, info['args'], info['kwargs'], info['priority']))
            if time.time() >= after_time:
                sorted(self._api_container, key=lambda priority: priority[-1])
                for fn, args, kwargs, _ in self._api_container:
                    result = fn(*args, **kwargs)

                    if not result.success:
                        debugger.debug(result.message)
                        # set log

                    set_redis(info['dest_key'], result.data)

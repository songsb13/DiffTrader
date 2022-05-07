"""
    이 파일은 sender등 여러개의 외부 도메인에서 사용하는 object가 들어있음.
    This file has object classes that used from variable external domains like sender.
"""

import json

from DiffTrader.GlobalSetting.settings import (
    APIPriority,
)
from DiffTrader.Util.utils import (
    publish_redis,
    DecimalDecoder
)

from multiprocessing import Process


class BaseProcess(Process):
    # base process for setter, monitoring and etc..
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

    def publish_redis_to_api_process(self, fn_name, publish_key, is_async=False, is_lazy=False, args=None, kwargs=None, api_priority=APIPriority.SEARCH):
        if args is None:
            args = []

        if kwargs is None:
            kwargs = {}

        publish_redis(publish_key, {
            'is_async': is_async,
            'is_lazy': is_lazy,
            'receive_type': self.receive_type,
            'fn_name': fn_name,
            'args': args,
            'kwargs': kwargs,
            'priority': api_priority,
        })

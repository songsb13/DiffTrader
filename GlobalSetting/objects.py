"""
    이 파일은 sender등 여러개의 외부 도메인에서 사용하는 object가 들어있음.
    This file has object classes that used from variable external domains like sender.
"""

import json
import time

from DiffTrader.GlobalSetting.settings import (
    APIPriority,
)
from DiffTrader.Util.utils import (
    publish_redis,
    DecimalDecoder
)

from DiffTrader.GlobalSetting.messages import CommonMessage as CMsg
from DiffTrader.GlobalSetting.messages import UtilMessage as UMsg


class MessageControlMixin(object):
    # base process for setter, monitoring and etc..
    receive_type = ''
    require_functions = []

    class Result:
        def __init__(self, success=False, data=None, message=''):
            self.success = success
            self.data = data
            self.message = message

    def get_subscribe_result(self, subscriber):
        for _ in range(3):
            api_contents = subscriber.get_message()
            result = self._unpacking_message(api_contents)
            if result.success:
                return result
            time.sleep(0.5)
        else:
            return result

    def _unpacking_message(self, api_contents):
        if api_contents:
            raw_data = api_contents.get('data', 1)
            if isinstance(raw_data, int):
                return self.Result(success=False, message=UMsg.Warning.INCORRECT_RAW_DATA)

            to_json = json.loads(raw_data, cls=DecimalDecoder)
            if not to_json:
                return self.Result(success=False, message=UMsg.Warning.RAW_DATA_IS_NULL)

            data = to_json.get(self.receive_type, None)
            if data is None:
                return self.Result(success=False, message=UMsg.Warning.RECEIVE_TYPE_DATA_IS_NULL)

            result = {}
            for key in data.keys():
                if key not in self.require_functions:
                    continue
                result[key] = data[key]
            else:
                return self.Result(success=True, data=result)

    def publish_redis_to_api_process(self, fn_name, publish_key, logging=None, is_async=False, is_lazy=False, args=None, kwargs=None, api_priority=APIPriority.SEARCH):
        if args is None:
            args = []

        if kwargs is None:
            kwargs = {}

        if logging:
            logging.debug(CMsg.entrance_with_parameter(
                self.publish_redis_to_api_process,
                (fn_name, publish_key, logging, is_async, is_lazy, args, kwargs, api_priority)
            ))

        publish_redis(publish_key, {
            'is_async': is_async,
            'is_lazy': is_lazy,
            'receive_type': self.receive_type,
            'fn_name': fn_name,
            'args': args,
            'kwargs': kwargs,
            'priority': api_priority,
        })

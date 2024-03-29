import requests
import time

from DiffTrader.utils.util import get_redis, FunctionExecutor
from DiffTrader.settings.base import RedisKey


class Sender(object):
    def sender(self):
        while True:
            send_information = get_redis(RedisKey.SendInformation)

            if not send_information:
                time.sleep(5)
                continue

            with FunctionExecutor(self._base_request, sleep_time=60) as executor:
                result = executor.loop_executor(
                    full_url_path=send_information["full_url_path"],
                    extra=send_information["extra"],
                )

    def _base_request(self, full_url_path, extra=None, header=None) -> dict:
        if header is None:
            header = dict()

        if extra is None:
            extra = dict()

        response = requests.post(url=full_url_path, json=extra, headers=header)

        result = response.json()

        return result

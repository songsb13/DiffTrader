from DiffTrader.trading.settings import MethodType
from Util.pyinstaller_patch import debugger

import threading
import requests


class SenderThread(threading.Thread):
    def __init__(self, data_receive_queue):
        super(SenderThread, self).__init__()
        self._data_receive_queue = data_receive_queue
        self.daemon = True

    def run(self):
        while True:
            try:
                method, url, information_dict = self._data_receive_queue

                parameter = information_dict.get('parameter', dict())
                after_process = information_dict.get('after_process', None)
                callback = information_dict.get('callback', None)
                callback_kwargs = information_dict.get('callback_kwargs', dict())

                if method == MethodType.GET:
                    rq = requests.get(url, json=parameter)
                elif method == MethodType.POST:
                    rq = requests.post(url, data=parameter)

                result = rq.json()

                if callback:
                    callback_result = callback(result) if not callback_kwargs \
                        else callback(**callback_kwargs)
                    if after_process:
                        after_process(callback_result)
            except Exception as ex:
                debugger.debug(ex)

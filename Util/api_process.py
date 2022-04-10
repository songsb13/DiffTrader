from multiprocessing import Process


class APIProcess(Process):
    def __init__(self, api_queue, exchange_keys):
        super(APIProcess, self).__init__()
        self._api_queue = api_queue
        self._api_container = []
        self._exchange_keys = exchange_keys

    def run(self) -> None:
        self._api_queue.get()

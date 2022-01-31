from DiffTrader.Util.utils import get_exchanges, subscribe_redis, get_min_profit, set_redis
from DiffTrader.GlobalSetting.settings import PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY, RedisKey
from DiffTrader.GlobalSetting.messages import MonitoringMessage as Msg
from Exchanges.settings import Consts
from Util.pyinstaller_patch import debugger

from multiprocessing import Process
from concurrent.futures import ThreadPoolExecutor

from decimal import Decimal

import time
import json
import datetime


class Setter(Process):
    def __init__(self, user, exchange, exchange_str):
        super(Setter, self).__init__()

        self._user = user
        self._exchange = exchange
        self._exchange_str = exchange_str
        print(user, exchange, exchange_str)

    def run(self) -> None:
        while True:
            print(self._exchange_str)
            time.sleep(1)
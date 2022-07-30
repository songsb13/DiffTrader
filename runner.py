from DiffTrader.Setter.setter import Setter
from DiffTrader.Monitoring.monitoring import Monitoring
from DiffTrader.Trading.trading import Trading
from DiffTrader.Withdrawal.withdrawal import Withdrawal

from DiffTrader.Util.utils import get_exchanges
from DiffTrader.Util.api_process import UpbitAPIProcess, BinanceAPIProcess
from DiffTrader.GlobalSetting.settings import TEST_USER
from DiffTrader.GlobalSetting.settings import RedisKey

from DiffTrader.apps.monitoring import LogTest as mLog
from DiffTrader.apps.setter import LogTest as sLog

import time
import os


TEST_EXCHANGES = ["Upbit", "Binance"]


for ps in [UpbitAPIProcess, BinanceAPIProcess]:
    ps().start()
#
#
# for each in TEST_EXCHANGES:
#     st = Setter(TEST_USER, each)
#     st.run()

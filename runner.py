from DiffTrader.apps.api_process import UpbitAPIProcess, BinanceAPIProcess
from DiffTrader.settings.base import TEST_USER
from DiffTrader.settings.base import RedisKey

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

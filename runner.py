from DiffTrader.Setter.setter import Setter
from DiffTrader.Monitoring.monitoring import Monitoring
from DiffTrader.Trading.trading import Trading
from DiffTrader.Withdrawal.withdrawal import Withdrawal

from DiffTrader.Util.utils import get_exchanges
from DiffTrader.Util.api_process import BaseAPIProcess
from DiffTrader.GlobalSetting.settings import TEST_USER
from DiffTrader.GlobalSetting.settings import RedisKey


from DiffTrader.Monitoring.monitoring import LogTest as mLog
from DiffTrader.Setter.setter import LogTest as sLog

import time


def run_for_log_test():
    t1 = mLog()
    t2 = sLog()
    while True:
        t1.logt()
        t2.logt()
        time.sleep(1)


if __name__ == '__main__':
    run_for_log_test()
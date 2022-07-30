from DiffTrader.apps.monitoring import LogTest as mLog
from DiffTrader.apps.setter import LogTest as sLog

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
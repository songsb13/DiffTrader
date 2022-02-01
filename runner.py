from DiffTrader.Setter.setter import Setter
from DiffTrader.Monitoring.monitoring import Monitoring

from DiffTrader.Util.utils import get_exchanges
from DiffTrader.GlobalSetting.settings import TEST_USER

import time


def run_setter():
    for exchange_str in exchanges.keys():
        setter = Setter(TEST_USER, exchange_str)
        setter.start()


def run_monitoring():
    available = list(exchanges.keys())
    for n, primary in enumerate(available):
        for secondary in list(available)[n+1:]:
            monitoring = Monitoring(TEST_USER, primary, secondary)
            monitoring.start()


def run():
    run_setter()
    run_monitoring()


if __name__ == '__main__':
    exchanges = get_exchanges()
    run()

    time.sleep(6000)

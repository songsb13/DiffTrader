from DiffTrader.Setter.setter import Setter
from DiffTrader.Monitoring.monitoring import Monitoring
from DiffTrader.Trading.trading import Trading
from DiffTrader.Withdrawal.withdrawal import Withdrawal

from DiffTrader.Util.utils import get_exchanges
from DiffTrader.Util.api_process import BaseAPIProcess
from DiffTrader.GlobalSetting.settings import TEST_USER


def run_api_processes():
    for exchange_str in exchanges.keys():
        api_process = BaseAPIProcess(exchange_str)
        api_process.start()


def run_setter():
    for exchange_str in exchanges.keys():
        setter = Setter(TEST_USER, exchange_str, api_queue)
        setter.start()


def run_monitoring():
    available = list(exchanges.keys())
    for n, primary in enumerate(available):
        for secondary in list(available)[n+1:]:
            monitoring = Monitoring(TEST_USER, primary, secondary, api_queue)
            monitoring.start()


def run_trading():
    trader = Trading(api_queue)
    trader.start()


def run_withdrawal():
    withdrawal = Withdrawal(api_queue)
    withdrawal.start()


def run():
    run_api_processes()
    run_setter()
    run_monitoring()
    run_trading()
    run_withdrawal()


if __name__ == '__main__':
    exchanges = get_exchanges()
    run()

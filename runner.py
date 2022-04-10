from DiffTrader.Setter.setter import Setter
from DiffTrader.Monitoring.monitoring import Monitoring
from DiffTrader.Trading.trading import Trading
from DiffTrader.Withdrawal.withdrawal import Withdrawal

from DiffTrader.Util.utils import get_exchanges
from DiffTrader.Util.api_process import APIProcess
from DiffTrader.GlobalSetting.settings import TEST_USER

from queue import PriorityQueue
from multiprocessing import Pipe, Lock
from multiprocessing.managers import SyncManager


def get_priority_queue():
    sync_m = SyncManager()
    sync_m.register("PriorityQueue", PriorityQueue)
    sync_m.start()
    queue_ = sync_m.PriorityQueue()

    return queue_


def run_api_process():
    api_process = APIProcess(api_queue, exchanges.keys())
    api_process.run()


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
    run_api_process()
    run_setter()
    run_monitoring()
    run_trading()
    run_withdrawal()


if __name__ == '__main__':
    exchanges = get_exchanges()
    api_queue = get_priority_queue()
    run()

    # time.sleep(6000)

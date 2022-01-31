from concurrent.futures import ProcessPoolExecutor

from DiffTrader.Setter.setter import Setter
from DiffTrader.Monitoring.monitoring import Monitoring
from DiffTrader.Trading.trading import Trading

from DiffTrader.Util.utils import get_exchanges
from DiffTrader.GlobalSetting.settings import AVAILABLE_EXCHANGES, TEST_USER


def run_setter():
    pass


def run_monitoring():
    pass


def run_trading():
    pass


if __name__ == '__main__':
    exchanges = get_exchanges()

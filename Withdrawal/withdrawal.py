from Exchanges.settings import *
from DiffTrader.Util.utils import get_exchanges, FunctionExecutor, set_redis, get_redis
from DiffTrader.GlobalSetting.settings import *
from Util.pyinstaller_patch import *

from concurrent.futures import ThreadPoolExecutor


class Withdrawal(object):
    def start_withdrawal(self, exchange, coin, send_amount, to_address, tag=None):
        """
            exchange: Exchange object
            coin: coin name, BTC, ETH, XRP and etc..
        """
        with FunctionExecutor(exchange.withdraw) as executor:
            result = executor.loop_executor(
                coin,
                send_amount,
                to_address,
                tag
            )

            if not result:
                return None

        while True:
            check_result = exchange.is_withdraw_completed(result['sai_id'])

            if check_result.success:
                return check_result

            time.sleep(60)

    def withdrawal(self):
        refreshed = 0
        thread_executor = ThreadPoolExecutor(max_workers=2)
        while True:
            trading_information = get_redis(RedisKey.TradingInformation)

            if not refreshed or refreshed + 3600 <= time.time():
                pass

            if not trading_information:
                continue

            primary_str, secondary_str = trading_information['from_exchange']['name'], \
                                         trading_information['to_exchange']['name']

            exchange_dict = get_exchanges()
            primary_exchange, secondary_exchange = exchange_dict[primary_str], exchange_dict[secondary_str]

            from_exchange_args = [
                primary_exchange
            ]
            to_exchange_args = [
                secondary_exchange
            ]

            from_exchange_withdrawal_result = thread_executor.submit(self.start_withdrawal, *from_exchange_args)
            to_exchange_withdrawal_result = thread_executor.submit(self.start_withdrawal, *to_exchange_args)

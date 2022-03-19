import time

from DiffTrader.Util.utils import get_exchanges, FunctionExecutor, set_redis, get_redis
from DiffTrader.GlobalSetting.settings import DEFAULT_REFRESH_TIME, RedisKey, SaiUrls
from Util.pyinstaller_patch import debugger

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
            debugger.debug(exchange.name)
            time.sleep(60)

    def withdrawal(self):
        refresh_time = 0
        thread_executor = ThreadPoolExecutor(max_workers=2)
        while True:
            trading_information = get_redis(RedisKey.TradingInformation)

            if not refresh_time or refresh_time <= time.time():
                refresh_time = time.time() + DEFAULT_REFRESH_TIME

            if not trading_information:
                continue

            primary_str, secondary_str = trading_information['from_exchange']['name'], \
                                         trading_information['to_exchange']['name']

            primary_exchange, secondary_exchange = exchange_dict[primary_str], exchange_dict[secondary_str]

            from_exchange_args = [
                primary_exchange
            ]
            to_exchange_args = [
                secondary_exchange
            ]

            from_exchange_withdrawal_result = thread_executor.submit(self.start_withdrawal, *from_exchange_args)
            to_exchange_withdrawal_result = thread_executor.submit(self.start_withdrawal, *to_exchange_args)

            total = dict(
                full_url_path=SaiUrls.BASE + SaiUrls.WITHDRAW,
                data=dict(
                    from_exchange_information=dict(exchange=primary_str, data=from_exchange_withdrawal_result),
                    to_exchange_information=dict(exchange=secondary_str, data=to_exchange_withdrawal_result)
                )
            )
            set_redis(RedisKey.SendInformation, total)

    def _get_exchanges_balance(self, primary_exchange, secondary_exchange):
        # balance
        results = []
        for exchange in [primary_exchange, secondary_exchange]:
            balance_result = exchange.get_balance()

            if not balance_result.success:
                debugger.debug(balance_result.message)
                return dict()

            results.append(balance_result.data)
        return results

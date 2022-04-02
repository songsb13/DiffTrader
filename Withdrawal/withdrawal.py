import time

from DiffTrader.Util.utils import get_exchanges, FunctionExecutor, set_redis, get_redis, get_withdrawal_info, get_auto_withdrawal
from DiffTrader.GlobalSetting.settings import TraderConsts, RedisKey, SaiUrls
from Exchanges.settings import Consts
from Util.pyinstaller_patch import debugger

from concurrent.futures import ThreadPoolExecutor
from decimal import getcontext, Decimal


getcontext().prec = 8


class WithdrawalInfo(object):
    def __init__(self):
        self._total_minimum_profit_amount = Decimal(0)

    def reset_total_minimum_profit_amount(self):
        self._total_minimum_profit_amount = Decimal(0)

    @property
    def total_minimum_profit_amount(self):
        return self._total_minimum_profit_amount

    @total_minimum_profit_amount.setter
    def total_minimum_profit_amount(self, value):
        self._total_minimum_profit_amount += value


class Withdrawal(object):
    def withdrawal(self):
        """
            primary_to_secondary로 거래가 된다고 했을 때, primary에서 coin을 매수, secondary에서 coin을 매도함.
            primary 거래소에서는 coin이 추가되고, secondary거래소에서는 btc가 추가된 상황
            코인 및 BTC의 매매수량이 n%이상이고, 총 이익발생이 m이상 되는경우 출금
            n, m = 유저 설정 값
            from_exchange = coin을 매수하는 거래소 -> Market(BTC, ETH등) 수량 체크 필요
            to_exchange = coin을 매도하는 거래소 -> coin 수량 체크 필요
        """
        refresh_time = 0
        thread_executor = ThreadPoolExecutor(max_workers=6)
        exchange_dict = get_exchanges()
        user_withdrawal_info = get_withdrawal_info()
        latest_info = WithdrawalInfo()
        while True:
            trading_information = get_redis(RedisKey.TradingInformation)
            if not get_auto_withdrawal():
                debugger.debug()
                continue

            if not refresh_time or refresh_time <= time.time():
                refresh_time = time.time() + TraderConsts.DEFAULT_REFRESH_TIME

            if not trading_information:
                continue
            latest_info.total_minimum_profit_amount(trading_information['btc_profit'])
            if latest_info.total_minimum_profit_amount < user_withdrawal_info['minimum_profit_amount']:
                continue

            from_str, to_str = (trading_information['from_exchange']['name'],
                                trading_information['to_exchange']['name'])

            from_exchange, to_exchange = (exchange_dict[from_str],
                                          exchange_dict[to_str])

            withdrawal_info = self._get_need_withdrawal_coins(from_exchange, to_exchange, user_withdrawal_info)

            executor_args_list = []
            if withdrawal_info:
                for coin, info in withdrawal_info.items():
                    executor_args_list.append(self.set_thread_executor(coin, info))

            latest_info.reset_total_minimum_profit_amount()
            tasks = []
            for args in executor_args_list:
                task = thread_executor.submit(self.start_withdrawal, *args)
                tasks.append(task)

            total = {}
            set_redis(RedisKey.SendInformation, total)

    def _get_need_withdrawal_coins(self, from_exchange, to_exchange, withdrawal_info):
        from_balance = from_exchange.get_balance(cached=True)
        to_balance = to_exchange.get_balance(cached=True)

        intersection = set(from_balance.keys()).intersection(list(to_balance.keys()))
        inter_balance = dict()
        for coin in intersection:
            from_amount, to_amount = from_balance[coin], to_balance[coin]
            difference_amount = from_amount - to_amount

            send_exchange, min_amount = (from_exchange, from_amount) if difference_amount > 0 \
                else (to_exchange, to_amount)

            difference_percent = (abs(difference_amount) / to_amount) * 100

            if difference_percent >= withdrawal_info['balance_withdrawal_percent']:
                inter_balance.update({coin: {
                    'send_exchange': send_exchange,
                    'send_amount': difference_amount / 2
                }})

        return inter_balance

    def set_thread_executor(self, coin, withdrawal_info):
        address_info = withdrawal_info['send_exchange'].get_cached_data(Consts.DEPOSIT_ADDRESS)
        coin_address = address_info.get(coin)
        coin_tag = address_info.get(coin + 'TAG', None)
        exchange_args = [
            withdrawal_info['send_exchange'],
            coin,
            withdrawal_info['send_amount'],
            coin_address,
            coin_tag
        ]

        return exchange_args

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
            check_result = exchange.is_withdrawal_completed(coin, result['sai_id'])

            if check_result.success:
                return check_result
            debugger.debug(exchange.name)
            time.sleep(60)

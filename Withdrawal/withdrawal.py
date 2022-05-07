import threading
import time

from DiffTrader.Util.utils import (
    get_exchanges,
    FunctionExecutor,
    set_redis,
    get_redis,
    get_withdrawal_info,
    get_auto_withdrawal,
    CustomPickle,
    subscribe_redis

)
from DiffTrader.GlobalSetting.settings import (
    TraderConsts,
    RedisKey,
    SaiUrls,
    PicklePath
)
from DiffTrader.GlobalSetting.objects import BaseProcess
from Exchanges.settings import Consts
from Util.pyinstaller_patch import debugger

from concurrent.futures import ThreadPoolExecutor
from decimal import getcontext, Decimal


getcontext().prec = 8


class WithdrawalInfo(object):
    def __init__(self):
        self.total_minimum_profit_amount = Decimal(0)

    def add_total_minimum_profit_amount(self, value):
        sum(self.total_minimum_profit_amount, value)

    def reset_total_minimum_profit_amount(self):
        self.total_minimum_profit_amount = Decimal(0)


class Withdrawal(BaseProcess):
    receive_type = 'withdrawal'
    require_functions = ['get_balance', 'get_deposit_addrs', 'get_transaction_fee']

    def __init__(self, user, primary_str, secondary_str):
        super(Withdrawal, self).__init__()

        self._user = user

        self._primary_str = primary_str
        self._secondary_str = secondary_str

    def run(self):
        """

        """
        _primary_subscriber = subscribe_redis(self._primary_str)
        _secondary_subscriber = subscribe_redis(self._secondary_str)

        self._exchange = get_exchanges()

        primary = self._exchange[self._primary_str]
        secondary = self._exchange[self._secondary_str]
        refresh_time = 0

        while True:
            trading_information = get_redis(RedisKey.TradingInformation)
            if not get_auto_withdrawal():
                debugger.debug()
                continue

            if not refresh_time or refresh_time <= time.time():
                refresh_time = time.time() + TraderConsts.DEFAULT_REFRESH_TIME

            if not trading_information:
                continue

            from_str, to_str = (trading_information['from_exchange']['name'],
                                trading_information['to_exchange']['name'])



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
        custom_pickle = CustomPickle(WithdrawalInfo(), PicklePath.WITHDRAWAL)
        latest_info = custom_pickle.obj
        while True:
            trading_information = get_redis(RedisKey.TradingInformation)
            if not get_auto_withdrawal():
                debugger.debug()
                continue

            if not refresh_time or refresh_time <= time.time():
                refresh_time = time.time() + TraderConsts.DEFAULT_REFRESH_TIME

            if not trading_information:
                continue
            latest_info.add_total_minimum_profit_amount(trading_information['btc_profit'])
            if latest_info.total_minimum_profit_amount < user_withdrawal_info['minimum_profit_amount']:
                continue

            from_str, to_str = (trading_information['from_exchange']['name'],
                                trading_information['to_exchange']['name'])

            if self._primary_subscriber is None and self._secondary_subscriber is None:
                self._primary_subscriber = subscribe_redis(RedisKey.ApiKey[from_str]['sub-apikey'])
                self._secondary_subscriber = subscribe_redis(RedisKey.ApiKey[to_str]['sub-apikey'])

            from_exchange, to_exchange = (exchange_dict[from_str],
                                          exchange_dict[to_str])

            withdrawal_info = self._get_need_withdrawal_coins(from_exchange, to_exchange, user_withdrawal_info)

            executor_args_list = []
            if withdrawal_info:
                for coin, info in withdrawal_info.items():
                    executor_args_list.append(self.set_thread_executor(coin, info))

            latest_info.reset_total_minimum_profit_amount()
            results = thread_executor.map(self.start_withdrawal, executor_args_list)

            return list(results)

    def _get_need_withdrawal_coins(self, from_exchange, to_exchange, withdrawal_info):
        self.pub_api_fn('get_balance', is_lazy=True)
        api_contents = self.api_subscriber.get_message()
        result = self.unpacking_message(api_contents)

        from_balance = result['get_balance']
        to_balance = result['get_balance']
        from_balance = from_exchange.get_balance(cached=True)
        to_balance = to_exchange.get_balance(cached=True)

        from_transaction_fee = from_exchange.get_cached_data(Consts.TRANSACTION_FEE)
        to_transaction_fee = to_exchange.get_cached_data(Consts.TRANSACTION_FEE)

        intersection = set(from_balance.keys()).intersection(list(to_balance.keys()))
        inter_balance = dict()
        for coin in intersection:
            from_amount, to_amount = ((from_balance[coin] - from_transaction_fee[coin]),
                                      (to_balance[coin] - to_transaction_fee[coin]))
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
        exchange_args = {
            "coin": coin,
            "coin_address": coin_address,
            "coin_tag": coin_tag,
            **withdrawal_info,
        }

        return exchange_args

    def start_withdrawal(self, info):
        """
            exchange: Exchange object
            coin: coin name, BTC, ETH, XRP and etc..
        """
        # exchange, coin, send_amount, to_address, tag=None
        with FunctionExecutor(info['exchange'].withdraw) as executor:
            result = executor.loop_executor(
                info['coin'],
                info['send_amount'],
                info['to_address'],
                info['tag']
            )

            if not result.success:
                return None

        while True:
            check_result = info['exchange'].is_withdrawal_completed(info['coin'], result.data['sai_id'])

            if check_result.success:
                send_information = {
                    'full_url_path': SaiUrls.BASE + SaiUrls.WITHDRAWAL,
                    **check_result.data
                }
                set_redis(RedisKey.SendInformation, send_information)
                return
            debugger.debug(info['exchange'].name)
            time.sleep(60)


if __name__ == '__main__':
    custom_pickle = CustomPickle(WithdrawalInfo(), PicklePath.WITHDRAWAL)
    pk = WithdrawalInfo()
    obj = custom_pickle.obj
    custom_pickle.obj = pk
    custom_pickle.save()
    print(obj)
    custom_pickle.load()
    print(obj)
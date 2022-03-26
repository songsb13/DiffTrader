import time

from DiffTrader.Util.utils import get_exchanges, FunctionExecutor, set_redis, get_redis, get_withdrawal_info, get_auto_withdrawal
from DiffTrader.GlobalSetting.settings import DEFAULT_REFRESH_TIME, RedisKey, SaiUrls
from Util.pyinstaller_patch import debugger

from concurrent.futures import ThreadPoolExecutor


class WithdrawalInfo(object):
    def __init__(self):
       self. current_profit = {}



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
        thread_executor = ThreadPoolExecutor(max_workers=2)
        exchange_dict = get_exchanges()
        withdrawal_info = get_withdrawal_info()
        current_profits = {}
        while True:
            trading_information = get_redis(RedisKey.TradingInformation)
            if not get_auto_withdrawal():
                debugger.debug()
                continue

            if not refresh_time or refresh_time <= time.time():
                refresh_time = time.time() + DEFAULT_REFRESH_TIME

            if not trading_information:
                continue

            from_exchange_str, to_exchange_str = (trading_information['from_exchange']['name'],
                                                  trading_information['to_exchange']['name'])
            from_exchange, to_exchange = exchange_dict[from_exchange_str], exchange_dict[to_exchange_str]

            if not self.check_able_withdrawal(from_exchange,
                                              to_exchange,
                                              withdrawal_info,
                                              trading_information):
                continue

            # exchange, coin, send_amount, to_address
            from_exchange_args = [
                from_exchange
            ]
            to_exchange_args = [
                to_exchange
            ]

            from_exchange_withdrawal_result = thread_executor.submit(self.start_withdrawal, *from_exchange_args)
            to_exchange_withdrawal_result = thread_executor.submit(self.start_withdrawal, *to_exchange_args)

            total = dict(
                full_url_path=SaiUrls.BASE + SaiUrls.WITHDRAW,
                data=dict(
                    from_exchange_information=dict(exchange=from_exchange_str, data=from_exchange_withdrawal_result),
                    to_exchange_information=dict(exchange=to_exchange_str, data=to_exchange_withdrawal_result)
                )
            )
            set_redis(RedisKey.SendInformation, total)

    def check_able_withdrawal(self, from_exchange, to_exchange, withdrawal_info, trading_information):
        market, coin = trading_information['sai_symbol'].split('_')

        from_balance = from_exchange.get_balance(cached=True)
        to_balance = to_exchange.get_balance(cached=True)

        market_balance = from_balance.get(market, None)
        coin_balance = to_balance.get(coin, None)

        market_balance

        if market_balance is None:
            pass

        if from_balance.get(market):
            'minimum_profit_amount'
            'balance_withdrawal_percent'

        return False

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

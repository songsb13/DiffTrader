import copy
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
    RedisKey,
    SaiUrls,
    PicklePath
)
from DiffTrader.GlobalSetting.objects import BaseProcess

from decimal import getcontext


getcontext().prec = 8


class Withdrawal(BaseProcess):
    receive_type = 'withdrawal'
    require_functions = ['get_balance', 'get_deposit_addrs', 'get_transaction_fee']

    def __init__(self, user, primary_str, secondary_str):
        super(Withdrawal, self).__init__()

        self._user = user

        self._primary_str = primary_str
        self._secondary_str = secondary_str

        self._primary_pub_key = RedisKey.ApiKey[self._primary_str]['publish']
        self._secondary_pub_key = RedisKey.ApiKey[self._secondary_str]['publish']

        self._primary_sub_key = RedisKey.ApiKey[self._primary_str]['subscribe']
        self._secondary_sub_key = RedisKey.ApiKey[self._secondary_str]['subscribe']

        self._pickle = CustomPickle(PicklePath.WITHDRAWAL)
        self._pickle.load()

        self._withdrew_dict = dict() if self._pickle.obj is None else self._pickle.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_pickle_withdrew_dict()

    def save_pickle_withdrew_dict(self):
        self._pickle.obj = self._withdrew_dict
        self._pickle.save()

    def run(self):
        """
            primary_to_secondary로 거래가 된다고 했을 때, primary에서 coin을 매수, secondary에서 coin을 매도함.
            primary 거래소에서는 coin이 추가되고, secondary거래소에서는 btc가 추가된 상황
            코인 및 BTC의 매매수량이 n%이상이고, 총 이익발생이 m이상 되는경우 출금
            n, m = 유저 설정 값
            from_exchange = coin을 매수하는 거래소 -> Market(BTC, ETH등) 수량 체크 필요
            to_exchange = coin을 매도하는 거래소 -> coin 수량 체크 필요

            흐름
            trading에서 정보 받는다 -> from, to exchange, order_id
            정보를 stack에 넣는다
            해당 스택은 송금이 완료되었다는 시그널을 받기 전까지 계속 진행된다.
            송금이 완료되었으면 해당 스택은 제거된다.
            밸런스는

            while True:
                api contents가 들어왔는지 확인한다.
                withdrawed
                need_withdrawal_dict가 있는지 확인한다.

        """

        exchange_dict = get_exchanges()
        subscriber_dict = {
            self._primary_str: subscribe_redis(self._primary_sub_key),
            self._secondary_str: subscribe_redis(self._secondary_sub_key)
        }
        user_withdrawal_info = get_withdrawal_info()

        self.publish_redis_to_api_process('get_balance', self._primary_pub_key, is_lazy=True)
        self.publish_redis_to_api_process('get_transaction_fee', self._primary_pub_key, is_lazy=True)

        self.publish_redis_to_api_process('get_balance', self._secondary_pub_key, is_lazy=True)
        self.publish_redis_to_api_process('get_transaction_fee', self._secondary_pub_key, is_lazy=True)

        while True:
            trading_information = get_redis(RedisKey.TradingInformation)
            if not get_auto_withdrawal():
                debugger.debug()
                continue

            if self._withdrew_dict:
                # check and execute sending to sender its withdrew.
                self.check_withdrawal_is_completed()

            if not trading_information:
                continue

            from_str, to_str = (trading_information['from_exchange']['name'],
                                trading_information['to_exchange']['name'])

            if not self._is_profit_subscribe_data({from_str, to_str}):
                continue

            from_exchange = exchange_dict[from_str]
            to_exchange = exchange_dict[to_str]

            from_subscriber = subscriber_dict[from_str]
            to_subscriber = subscriber_dict[to_str]

            from_contents = self.get_subscriber_api_contents(from_subscriber)
            to_contents = self.get_subscriber_api_contents(to_subscriber)

            if not from_contents or not to_contents:
                debugger.debug('fail-to-get-contents')
                time.sleep(5)
                continue

            subscribe_info = {
                'from': {
                    'exchange': from_exchange,
                    **from_contents
                },
                'to': {
                    'exchange': to_exchange,
                    **to_contents
                }
            }
            need_to_withdrawal_dict = self.check_coins_need_to_withdrawal(subscribe_info, user_withdrawal_info)
            if need_to_withdrawal_dict:
                for coin, info in need_to_withdrawal_dict.items():
                    if coin in self._withdrew_dict.keys():
                        # 중복 방지, 이미 출금한 코인을 여러번 출금 못하게 하기.
                        debugger.debug('already-in-withdrawal.')
                        continue
                    with FunctionExecutor(info['exchange'].withdraw) as executor:
                        result = executor.loop_executor(
                            info['coin'],
                            info['send_amount'],
                            info['to_address'],
                            info['tag']
                        )

                        if not result.success:
                            debugger.debug('fail-to-withdrawal.')
                            continue
                        else:
                            debugger.debug('success withdrawal')
                            self._withdrew_dict[coin] = {
                                'execute_info': info,
                                'result_data': result.data
                            }
                            self.save_pickle_withdrew_dict()

    def _is_profit_subscribe_data(self, string_set):
        return {self._primary_str, self._secondary_str} == string_set

    def get_subscriber_api_contents(self, subscriber):
        result = self.get_subscribe_result(subscriber)

        balance = result.get('get_balance')
        transaction_fee = result.get('transaction_fee')

        return {'balance': balance, 'transaction_fee': transaction_fee}

    def check_coins_need_to_withdrawal(self, subscribe_info, withdrawal_info):
        from_info = subscribe_info['from']
        to_info = subscribe_info['to']

        intersection = set(from_info['balance'].keys()).intersection(list(to_info['balance'].keys()))
        need_to_withdrawal_dict = dict()
        for coin in intersection:
            from_amount, to_amount = ((from_info['balance'][coin] - from_info['transaction_fee'][coin]),
                                      (to_info['balance'][coin] - to_info['transaction_fee'][coin]))
            difference_amount = from_amount - to_amount

            send_exchange, min_amount = (from_info['exchange'], from_amount) if difference_amount > 0 \
                else (to_info['exchange'], to_amount)

            difference_percent = (abs(difference_amount) / to_amount) * 100

            if difference_percent >= withdrawal_info['balance_withdrawal_percent']:
                need_to_withdrawal_dict.update({coin: {
                    'send_exchange': send_exchange,
                    'send_amount': difference_amount / 2
                }})

        return need_to_withdrawal_dict

    def check_withdrawal_is_completed(self):
        # check & execute
        copied_withdrew_dict = copy.deepcopy(self._withdrew_dict)
        for coin, info in copied_withdrew_dict:
            check_result = info['execute_info']['exchange'].is_withdrawal_completed(
                coin, info['result_data']['sai_id']
            )

            if check_result.success:
                send_information = {
                    'full_url_path': SaiUrls.BASE + SaiUrls.WITHDRAWAL,
                    **check_result.data
                }
                set_redis(RedisKey.SendInformation, send_information)
                debugger.debug()

                # remove coin-key to avoid checking withdraw
                self._withdrew_dict.pop(coin)

                self.save_pickle_withdrew_dict()

        return self._withdrew_dict

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
    pass
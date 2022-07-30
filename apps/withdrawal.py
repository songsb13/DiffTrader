"""
    목적
        1. Trading이 완료되어 발생한 결과 데이터를 바탕으로 출금을 실행하고, 출금 결과를 저장한다.
        2. 저장된 출금 결과를 보고 입금이 최종적으로 끝났는지 확인한다.

    기타
        1. 발생 가능한 Process의 수는 triangle number 형태이다.
        2. 프로그램 시작 시 실행 유저, 출금되는 거래소와 입금받는 거래소를 받는다.
        3. Redis는 Sub-Pub 형태이며 각 Process는 자신이 담당하는 거래소간의 결과 데이터인지 확인한다.
        4. 프로그램 종료 시 입금이 최종적으로 끝나지 않은 값을 Pickle로 저장한다.
"""

import copy
import time
import logging.config


from DiffTrader.settings.message import (
    WithdrawalMessage as Msg,
    CommonMessage as CMsg
)

from DiffTrader.utils.util import (
    get_exchanges,
    FunctionExecutor,
    set_redis,
    get_redis,
    get_withdrawal_info,
    get_auto_withdrawal,
    CustomPickle,
    subscribe_redis
)
from DiffTrader.utils.logger import SetLogger

from DiffTrader.settings.base import (
    RedisKey,
    SaiUrls,
    PicklePath
)
from DiffTrader.settings.objects import MessageControlMixin

from decimal import getcontext

__file__ = 'monitoring.py'


logging_config = SetLogger.get_config_base_process(__file__)
logging.config.dictConfig(logging_config)


getcontext().prec = 8


class Withdrawal(MessageControlMixin):
    name, name_kor = 'Withdrawal', '출금'
    receive_type = 'withdrawal'
    require_functions = ['get_balance', 'get_deposit_addrs', 'get_transaction_fee']

    def __init__(self, user, primary_str, secondary_str):
        logging.info(CMsg.START)
        logging.debug(Msg.Debug.SET_WITHDRAWAL.format(primary_str, secondary_str, user))
        self._user = user

        self._primary_str = primary_str
        self._secondary_str = secondary_str

        self._primary_pub_key = RedisKey.ApiKey[self._primary_str]['publish']['withdrawal']
        self._secondary_pub_key = RedisKey.ApiKey[self._secondary_str]['publish']['withdrawal']

        self._primary_sub_key = RedisKey.ApiKey[self._primary_str]['subscribe']['withdrawal']
        self._secondary_sub_key = RedisKey.ApiKey[self._secondary_str]['subscribe']['withdrawal']

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
            1. 정
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
            if self._withdrew_dict:
                # check and execute sending to sender its withdrew.
                logging.debug(Msg.Debug.WITHDREW_DICT)
                self.check_withdrawal_is_completed()

            if not trading_information:
                continue

            from_str, to_str = (trading_information['from_exchange']['name'],
                                trading_information['to_exchange']['name'])

            if not self._is_profit_subscribe_data({from_str, to_str}):
                time.sleep(5)
                continue

            from_exchange = exchange_dict[from_str]
            to_exchange = exchange_dict[to_str]

            from_subscriber = subscriber_dict[from_str]
            to_subscriber = subscriber_dict[to_str]

            from_contents = self.get_subscriber_api_contents(from_subscriber)
            to_contents = self.get_subscriber_api_contents(to_subscriber)

            if not from_contents or not to_contents:
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
                        continue
                    if not get_auto_withdrawal():
                        logging.info(Msg.Info.MANUAL_WITHDRAWAL)
                        logging.info(Msg.Info.MANUAL_INFO.format(
                            info['exchange'].name,
                            info['coin'],
                            info['send_amount'],
                            info['to_address'],
                            info['tag']
                        ))
                        continue

                    with FunctionExecutor(info['exchange'].withdraw) as executor:
                        result = executor.loop_executor(
                            info['coin'],
                            info['send_amount'],
                            info['to_address'],
                            info['tag']
                        )

                        if not result.success:
                            logging.info(Msg.Info.REQUEST_FAIL.format(result.msg))
                            continue
                        else:
                            logging.info(Msg.Info.REQUEST_SUCCESS)
                            self._withdrew_dict[coin] = {
                                'execute_info': info,
                                'result_data': result.data
                            }
                            self.save_pickle_withdrew_dict()

    def _is_profit_subscribe_data(self, string_set):
        return {self._primary_str, self._secondary_str} == string_set

    def get_subscriber_api_contents(self, subscriber):
        logging.debug(CMsg.entrance_with_parameter(self.get_subscribe_result, (subscriber,)))
        result = self.get_subscribe_result(subscriber)

        if not result:
            logging.warning(result.message)
            return dict()

        balance = result.data.get('get_balance')
        transaction_fee = result.data.get('transaction_fee')

        if balance is None or transaction_fee is None:
            return dict()

        return {'balance': balance, 'transaction_fee': transaction_fee}

    def check_coins_need_to_withdrawal(self, subscribe_info, withdrawal_info):
        logging.debug(CMsg.entrance_with_parameter(
            self.check_coins_need_to_withdrawal,
            (subscribe_info, withdrawal_info)
        ))
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
        logging.debug(Msg.Debug.NEED_TO_WITHDRAWAL_DICT.format(need_to_withdrawal_dict))
        return need_to_withdrawal_dict

    def check_withdrawal_is_completed(self):
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
                logging.debug(Msg.Debug.COMPLETED)

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
            logging.debug(Msg.Debug.ON_WITHDRAW.format(info['exchange'].name, info['coin']))
            time.sleep(60)


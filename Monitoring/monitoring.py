"""
    목적
        1. Setter process로부터 받은 거래소 데이터와 websocket을 통해 가져오는 orderbook으로 최고 수익을 내는 코인을 파악한다.
        2. 최고 수익을 내는 코인과 관련 결과 값을 Trading process로 보낸다.

    기타
        1. 발생 가능한 Proces의 수는 triangle number 형태이다.
        2. 해당 프로세스는 각 거래소의 websocket을 연결하고, orderbook을 가져온다.
        3. 유저가 입력한 최소 BTC profit을 넘는 경우 trading process로 거래 관련 데이터를 set한다.
"""

from DiffTrader.Util.utils import get_exchanges, subscribe_redis, get_min_profit, set_redis, DecimalDecoder, task_wrapper
from DiffTrader.Util.logger import SetLogger
from DiffTrader.GlobalSetting.settings import (TraderConsts, RedisKey, DEBUG, TEST_USER, Domains)
from DiffTrader.GlobalSetting.messages import MonitoringMessage as Msg
from DiffTrader.GlobalSetting.messages import CommonMessage as CMsg
from DiffTrader.GlobalSetting.test_settings import UPBIT_TEST_INFORMATION, BINANCE_TEST_INFORMATION
from Exchanges.settings import Consts

from decimal import Decimal

import time
import json
import datetime
import asyncio
import logging.config


__file__ = 'monitoring.py'


logging_config = SetLogger.get_config_base_process(__file__)
logging.config.dictConfig(logging_config)


class Monitoring(object):
    name, name_kor = Domains.MONITORING, '모니터링'

    def __init__(self, user, primary_str, secondary_str):
        logging.info(CMsg.START)
        logging.debug(Msg.Debug.SET_MONITORING.format(primary_str, secondary_str, user))
        super(Monitoring, self).__init__()
        self._user = user

        self._primary_str = primary_str
        self._secondary_str = secondary_str

        self._min_profit = get_min_profit()

        self._exchanges = None
        self._primary = None
        self._secondary = None

        self._set_orderbook_subscribe_flag = False
        self._set_candle_subscribe_flag = False

    def run(self) -> None:
        _primary_subscriber = subscribe_redis(self._primary_str, logging=logging)
        _secondary_subscriber = subscribe_redis(self._secondary_str, logging=logging)

        self._exchanges = get_exchanges()

        primary = self._exchanges[self._primary_str]
        secondary = self._exchanges[self._secondary_str]

        latest_primary_information, latest_secondary_information = dict(), dict()
        while True:
            if not DEBUG:
                primary_contents = _primary_subscriber.get_message()
                secondary_contents = _secondary_subscriber.get_message()

                if primary_contents and secondary_contents:
                    primary_information = primary_contents.get('data', 1)
                    secondary_information = secondary_contents.get('data', 1)
                    if isinstance(primary_information, int) or isinstance(secondary_information, int):
                        time.sleep(1)
                        continue
                    latest_primary_information = json.loads(primary_information, cls=DecimalDecoder)
                    latest_secondary_information = json.loads(secondary_information, cls=DecimalDecoder)

                    logging.debug(Msg.Debug.GET_INFORMATION.format(latest_primary_information, latest_secondary_information))

                elif not latest_primary_information and not latest_secondary_information:
                    logging.debug(Msg.Debug.WAIT_INFORMATION)
                    time.sleep(1)
                    continue
            else:
                # test code
                latest_primary_information = json.loads(UPBIT_TEST_INFORMATION, cls=DecimalDecoder)
                latest_secondary_information = json.loads(BINANCE_TEST_INFORMATION, cls=DecimalDecoder)
            tradable_symbol_list = self._get_tradable_symbols(latest_primary_information,
                                                              latest_secondary_information)

            if not self._set_orderbook_subscribe_flag:
                self._set_orderbook_subscribe_flag = True
                self._set_orderbook_subscribe(primary, secondary, tradable_symbol_list)
            arbitrage_data = self.get_arbitrage_primary_secondary(primary, secondary, tradable_symbol_list)

            if not arbitrage_data:
                logging.debug(Msg.Debug.FAIL_TO_GET_ORDERBOOK)
                continue

            profit_dict = self._get_max_profit(primary,
                                               secondary,
                                               latest_primary_information,
                                               latest_secondary_information,
                                               arbitrage_data)
            if not profit_dict or self._min_profit > profit_dict['btc_profit']:
                logging.info(Msg.Info.ALL_COINS_NOT_REACHED_EXPECTED_PROFIT)
                time.sleep(5)
                continue

            set_redis(RedisKey.ProfitInformation, profit_dict, use_decimal=True, logging=logging)

    def _get_tradable_symbols(self, primary_information, secondary_information):
        """
            primary - secondary 간 출금 가능한 코인과
            프로그램 상 지정된 마켓을 확인하고,
            거래 가능한 symbols로 리턴
        """
        logging.debug(CMsg.entrance_with_parameter(
            self._get_tradable_symbols,
            (primary_information, secondary_information)
        ))
        primary_deposit_symbols = primary_information['deposit'].keys()
        secondary_deposit_symbols = secondary_information['deposit'].keys()
        deposit_intersection = set(primary_deposit_symbols).intersection(secondary_deposit_symbols)

        able_markets = set(TraderConsts.ABLE_MARKETS).intersection(deposit_intersection)
        able_sai_symbols = list()
        for market in able_markets:
            for coin in deposit_intersection:
                if market == coin:
                    continue
                able_sai_symbols.append(f'{market}_{coin}')
        return able_sai_symbols

    def _set_orderbook_subscribe(self, primary, secondary, tradable_symbol_list):
        """
            subscriber 웹소켓 스레드를 실행하고
            orderbook을 subscribe하는 함수
        """
        logging.debug(CMsg.entrance_with_parameter(
            self._set_orderbook_subscribe,
            (primary, secondary, tradable_symbol_list)
        ))
        primary.set_subscriber()
        secondary.set_subscriber()

        primary.set_subscribe_orderbook(tradable_symbol_list)
        secondary.set_subscribe_orderbook(tradable_symbol_list)

        return

    def get_arbitrage_primary_secondary(self, primary, secondary, tradable_symbol_list):
        """
            tradable_symbol_list에서 평균 ask & bid 값을 async하게 가져오고,
            거래소 간 차익을 계산하는 함수
        """
        logging.debug(CMsg.entrance_with_parameter(
            self.get_arbitrage_primary_secondary,
            (primary, secondary, tradable_symbol_list)
        ))

        def __bid_ask_calculator(bids, asks):
            if not bids or not asks:
                return 0

            return Decimal((bids - asks) / asks).quantize(Decimal(10) ** -8)

        task_list = [
            {'fn': primary.get_curr_avg_orderbook},
            {'fn': secondary.get_curr_avg_orderbook}
        ]

        primary_result, secondary_result = asyncio.run(task_wrapper(task_list))
        success = primary_result.success and secondary_result.success
        if success:
            primary_to_secondary = dict()
            secondary_to_primary = dict()
            calculated_symbol_list = set()
            for sai_symbol in tradable_symbol_list:
                if sai_symbol not in primary_result.data or sai_symbol not in secondary_result.data:
                    # orderbook에 아직 충분한 데이터가 쌓이지 않은 상태인 경우 값에 들어가있지 않으므로 키에러가 발생할 수 있음.
                    continue
                primary_asks = primary_result.data[sai_symbol][Consts.ASKS]
                secondary_bids = secondary_result.data[sai_symbol][Consts.BIDS]
                primary_to_secondary_result = __bid_ask_calculator(secondary_bids, primary_asks)

                if not primary_to_secondary_result:
                    continue
                primary_to_secondary[sai_symbol] = primary_to_secondary_result

                primary_bids = primary_result.data[sai_symbol][Consts.BIDS]
                secondary_asks = secondary_result.data[sai_symbol][Consts.ASKS]
                secondary_to_primary_result = __bid_ask_calculator(primary_bids, secondary_asks)

                if not secondary_to_primary_result:
                    continue
                secondary_to_primary[sai_symbol] = secondary_to_primary_result
                calculated_symbol_list.add(sai_symbol)
            data = {
                'primary': primary_result.data,
                'secondary': secondary_result.data,
                'calculated_symbol_list': list(calculated_symbol_list),
                'expected_profit_dict': {
                    TraderConsts.PRIMARY_TO_SECONDARY: primary_to_secondary,
                    TraderConsts.SECONDARY_TO_PRIMARY: secondary_to_primary
                }
            }

            return data

        else:
            wait_time = max(primary_result.wait_time, secondary_result.wait_time)
            time.sleep(wait_time)
            error_message = '\n'.join([primary_result.message, secondary_result.message])
            logging.debug(Msg.Debug.GET_ERROR_MESSAGE_IN_COMPARE.format(error_message))
            return dict()

    def _get_max_profit(self, primary, secondary, primary_information, secondary_information, arbitrage_data):
        """
            계산된 arbitrage_data를 바탕으로
            거래 가능한 코인들 중 가장 높은 이익을 내는 코인을 찾는 함수.
        """
        def __expectation_setter(exchange, information, orderbook):
            return {
                'exchange': exchange,
                'information': information,
                'orderbook': orderbook
            }

        logging.debug(CMsg.entrance_with_parameter(
            self._get_max_profit,
            (primary, secondary, primary_information, secondary_information, arbitrage_data)
        ))
        profit_dict = dict()
        for exchange_running_type in [TraderConsts.PRIMARY_TO_SECONDARY, TraderConsts.SECONDARY_TO_PRIMARY]:
            for sai_symbol in arbitrage_data['calculated_symbol_list']:
                market, coin = sai_symbol.split('_')

                if not primary_information['balance'].get(coin):
                    logging.warning(Msg.Debug.BALANCE_NOT_FOUND.format(self._primary_str, sai_symbol))
                    time.sleep(10)
                    continue

                elif not secondary_information['balance'].get(coin):
                    logging.warning(Msg.Debug.BALANCE_NOT_FOUND.format(self._secondary_str, sai_symbol))
                    time.sleep(10)
                    continue

                expect_profit_percent = arbitrage_data['expected_profit_dict'][exchange_running_type][sai_symbol]

                if not DEBUG and expect_profit_percent < self._min_profit:
                    logging.info(Msg.Info.COIN_NOT_REACHED_EXPECTED_PROFIT.format(coin, expect_profit_percent, self._min_profit))
                    continue

                if exchange_running_type == TraderConsts.PRIMARY_TO_SECONDARY:
                    expectation_data = {
                        'from': __expectation_setter(primary, primary_information, arbitrage_data['primary']),
                        'to': __expectation_setter(secondary, secondary_information, arbitrage_data['secondary'])
                    }
                else:
                    expectation_data = {
                        'from': __expectation_setter(secondary, secondary_information, arbitrage_data['secondary']),
                        'to': __expectation_setter(primary, primary_information, arbitrage_data['primary']),
                    }
                tradable_btc, coin_amount, sell_coin_amount, btc_profit, real_difference = self._get_expectation(
                    expectation_data,
                    expect_profit_percent,
                    sai_symbol,
                )

                logging.debug(Msg.Debug.TRADABLE_INFO.format(tradable_btc, coin_amount, sell_coin_amount,
                                                             btc_profit, real_difference))

                if not profit_dict and (tradable_btc, coin_amount):
                    refresh_profit_dict = True
                elif profit_dict['btc_profit'] < btc_profit:
                    refresh_profit_dict = True
                else:
                    refresh_profit_dict = False

                if refresh_profit_dict:
                    profit_dict = {
                        'btc_profit': btc_profit,
                        'tradable_btc': tradable_btc,
                        'coin_amount': coin_amount,
                        'sell_coin_amount': sell_coin_amount,
                        'exchange_running_type': exchange_running_type,
                        'sai_symbol': sai_symbol,
                        'additional_information': {
                            'user': self._user,
                            'real_difference': real_difference,
                            'created_time': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),

                            'from_exchange_str': expectation_data['from']['exchange'].name,

                            'to_exchange_str': expectation_data['to']['exchange'].name,
                            'arbitrage_data': arbitrage_data
                        }
                    }
        return profit_dict

    def _get_expectation(self, expectation_data, expected_profit_percent, sai_symbol):
        """
            예상 차익을 구하고, 팔아야하는 coin amount 수량을 확인하는 함수

        """
        def __find_min_balance(btc_amount, coin_amount, to_exchange_coin_bid):
            coin_to_btc_price = coin_amount * to_exchange_coin_bid
            tradable_btc = btc_amount if btc_amount < coin_to_btc_price else coin_to_btc_price

            return tradable_btc

        def __get_real_difference(from_information, to_information, expected_profit_percent, market):
            # transaction fee에 대한 검증은 get_expectation 에서 진행
            from_trading_fee_percent = (1 - from_information['trading_fee'][market]) ** from_information['fee_count']
            to_trading_fee_percent = (1 - to_information['trading_fee'][market]) ** to_information['fee_count']

            real_diff = ((1 + expected_profit_percent) * from_trading_fee_percent * to_trading_fee_percent) - 1

            return real_diff

        logging.debug(CMsg.entrance_with_parameter(
            self._get_expectation,
            (expectation_data, expected_profit_percent, sai_symbol)
        ))
        market, coin = sai_symbol.split('_')
        from_, to_ = expectation_data['from'], expectation_data['to']

        to_exchange_coin_amount = to_['information']['balance'][coin]
        real_difference = __get_real_difference(
            from_['information'],
            to_['information'],
            expected_profit_percent,
            market
        )
        tradable_btc = __find_min_balance(
            from_['information']['balance'][market],
            to_exchange_coin_amount,
            to_['orderbook'][sai_symbol][Consts.BIDS],
        )

        # coin_amount that calculate trading and transaction fees.
        # sell coin amount that to_exchange.
        sell_coin_amount = to_['exchange'].base_to_coin(
            tradable_btc,
            from_['information']['trading_fee'][market],
        )

        btc_profit = tradable_btc * real_difference

        return tradable_btc, to_exchange_coin_amount, sell_coin_amount, btc_profit, real_difference


if __name__ == '__main__':
    st = Monitoring(TEST_USER, 'Upbit', 'Binance')
    st.run()

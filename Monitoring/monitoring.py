from DiffTrader.Util.utils import get_exchanges, subscribe_redis, get_min_profit, set_redis, DecimalDecoder, task_wrapper
from DiffTrader.GlobalSetting.settings import PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY, RedisKey, DEBUG, TEST_USER, ABLE_MARKETS
from DiffTrader.GlobalSetting.messages import MonitoringMessage as Msg
from DiffTrader.GlobalSetting.test_settings import UPBIT_TEST_INFORMATION, BINANCE_TEST_INFORMATION
from Exchanges.settings import Consts
from Util.pyinstaller_patch import debugger

from multiprocessing import Process
from concurrent.futures import ThreadPoolExecutor

from decimal import Decimal

import time
import json
import datetime
import asyncio


class Monitoring(Process):
    def __init__(self, user, primary_str, secondary_str):
        debugger.debug(Msg.START.format(primary_str, secondary_str, user))

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
        debugger.debug(Msg.RUNNING.format(self._primary_str, self._secondary_str, self._user))
        _primary_subscriber = subscribe_redis(self._primary_str)
        _secondary_subscriber = subscribe_redis(self._secondary_str)

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
                    if primary_information == 1 or secondary_information == 1:
                        time.sleep(1)
                        continue
                    latest_primary_information = json.loads(primary_information, cls=DecimalDecoder)
                    latest_secondary_information = json.loads(secondary_information, cls=DecimalDecoder)

                elif not latest_primary_information and not latest_secondary_information:
                    time.sleep(1)
                    continue
            else:
                # test code
                latest_primary_information = json.loads(UPBIT_TEST_INFORMATION, cls=DecimalDecoder)
                latest_secondary_information = json.loads(BINANCE_TEST_INFORMATION, cls=DecimalDecoder)
            sai_symbol_intersection = self._get_available_symbols(latest_primary_information,
                                                                  latest_secondary_information)

            if not self._set_orderbook_subscribe_flag:
                self._set_orderbook_subscribe_flag = True
                self._set_orderbook_subscribe(primary, secondary, sai_symbol_intersection)
            orderbook_success, total_orderbooks = self._compare_orderbook(primary, secondary, sai_symbol_intersection)

            if not orderbook_success:
                debugger.debug(Msg.FAIL_TO_GET_ORDERBOOK)
                continue

            profit_dict = self._get_max_profit(latest_primary_information, latest_secondary_information,
                                               sai_symbol_intersection, total_orderbooks)
            if not profit_dict:
                debugger.debug(Msg.FAIL_TO_GET_SUITABLE_PROFIT)
                continue

            if profit_dict['btc_profit'] >= self._min_profit:
                debugger.debug(Msg.SET_PROFIT_DICT(self._min_profit, profit_dict))
                set_redis(RedisKey.ProfitInformation, profit_dict)

    def _get_available_symbols(self, primary_information, secondary_information):
        primary_deposit_symbols = primary_information['deposit'].keys()
        secondary_deposit_symbols = secondary_information['deposit'].keys()
        deposit_intersection = set(primary_deposit_symbols).intersection(secondary_deposit_symbols)

        # set market
        able_markets = set(ABLE_MARKETS).intersection(deposit_intersection)
        able_sai_symbols = list()
        for market in able_markets:
            for coin in deposit_intersection:
                if market == coin:
                    continue
                able_sai_symbols.append(f'{market}_{coin}')
        return able_sai_symbols

    def _set_orderbook_subscribe(self, primary, secondary, symbol_list):
        primary.set_subscriber()
        secondary.set_subscriber()

        primary.set_subscribe_orderbook(symbol_list)
        secondary.set_subscribe_orderbook(symbol_list)

        return

    def _compare_orderbook(self, primary, secondary, sai_symbol_intersection, default_btc=1):
        task_list = [
            {'fn': primary.get_curr_avg_orderbook},
            {'fn': secondary.get_curr_avg_orderbook}
        ]

        primary_result, secondary_result = asyncio.run(task_wrapper(task_list))
        success = primary_result.success and secondary_result.success
        if success:
            primary_to_secondary = dict()
            secondary_to_primary = dict()
            for sai_symbol in sai_symbol_intersection:
                primary_asks = primary_result.data[sai_symbol][Consts.ASKS]
                secondary_bids = secondary_result.data[sai_symbol][Consts.BIDS]

                primary_to_secondary[sai_symbol] = Decimal(
                    (secondary_bids - primary_asks) / primary_asks
                ).quantize(Decimal(10) ** -8)

                primary_bids = primary_result.data[sai_symbol][Consts.BIDS]
                secondary_asks = secondary_result.data[sai_symbol][Consts.ASKS]

                secondary_to_primary[sai_symbol] = Decimal(
                    (primary_bids - secondary_asks) / secondary_asks
                ).quantize(Decimal(10) ** -8)

            data = {
                'primary_orderbook': primary_result.data,
                'secondary_orderbook': secondary_result.data,
                'expected_profit_dict': {
                    Consts.PRIMARY_TO_SECONDARY: primary_to_secondary,
                    Consts.SECONDARY_TO_PRIMARY: secondary_to_primary
                }
            }

            return True, data

        else:
            wait_time = max(primary_result.wait_time, secondary_result.wait_time)
            time.sleep(wait_time)
            error_message = '\n'.join([primary_result.message, secondary_result.message])
            debugger.debug(Msg.GET_ERROR_MESSAGE_IN_COMPARE.format(error_message))
            return False, error_message

    def _get_max_profit(self, primary_information, secondary_information, sai_symbol_intersection, total_orderbooks):
        profit_dict = dict()
        for exchange_running_type in [PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY]:
            for sai_symbol in sai_symbol_intersection:
                market, coin = sai_symbol.split('_')

                if not primary_information['balance'].get(coin):
                    debugger.debug(Msg.BALANCE_NOT_FOUND.format(self._primary_str, sai_symbol))
                    continue

                elif not secondary_information['balance'].get(coin):
                    debugger.debug(Msg.BALANCE_NOT_FOUND.format(self._secondary, sai_symbol))
                    continue

                expect_profit_percent = total_orderbooks['expected_profit_dict'][exchange_running_type][sai_symbol]

                if expect_profit_percent < self._min_profit:
                    debugger.debug(Msg.EXPECTED_PROFIT.format(sai_symbol, expect_profit_percent, self._min_profit))
                    continue

                if exchange_running_type == PRIMARY_TO_SECONDARY:
                    expectation_data = {
                        'from': {
                            'information': primary_information,
                            'orderbook': total_orderbooks['primary']
                        },
                        'to': {
                            'information': secondary_information,
                            'orderbook': total_orderbooks['secondary']
                        }
                    }
                else:
                    expectation_data = {
                        'from': {
                            'information': secondary_information,
                            'orderbook': total_orderbooks['secondary']
                        },
                        'to': {
                            'information': primary_information,
                            'orderbook': total_orderbooks['primary']
                        }
                    }
                tradable_btc, coin_amount, btc_profit, real_difference = self._get_expectation(
                    expectation_data,
                    expect_profit_percent,
                    sai_symbol,
                )

                debugger.debug(Msg.TRADABLE_INFO(tradable_btc, coin_amount, btc_profit, real_difference))

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
                        'additional_information': {
                            'user': self._user,
                            'real_difference': real_difference,
                            'created_time': datetime.datetime.now(),
                            'primary': self._primary_str,
                            'secondary': self._secondary_str,
                            'sai_symbol': sai_symbol,
                            'total_orderbooks': total_orderbooks
                        }
                    }

        return profit_dict

    def _get_expectation(self, expectation_data, expected_profit_percent, sai_symbol):
        market, coin = sai_symbol.split('_')
        from_, to_ = expectation_data['from'], expectation_data['to']

        real_difference = self._get_real_difference(
            from_['information'],
            to_['information'],
            expected_profit_percent
        )
        tradable_btc, alt_amount = self._find_min_balance(
            from_['information']['balance']['BTC'],
            to_['information']['balance'][coin],
            to_['orderbook'][sai_symbol],
        )

        btc_profit = (tradable_btc * real_difference) - \
                     (from_['information'][sai_symbol][coin] * from_['orderbook'][sai_symbol][Consts.ASKS]) - \
                     to_['information']['transaction_fee']['BTC']

        return tradable_btc, alt_amount, btc_profit, real_difference

    def _get_real_difference(self, from_information, to_information, expected_profit_percent):
        # transaction fee에 대한 검증은 get_expectation 에서 진행
        from_trading_fee_percent = (1 - from_information['trading_fee']) ** from_information['fee_count']
        to_trading_fee_percent = (1 - to_information['trading_fee']) ** to_information['fee_count']

        real_diff = ((1 + expected_profit_percent) * from_trading_fee_percent * to_trading_fee_percent) - 1

        return Decimal(real_diff).quantize(Decimal(10) ** -8)

    def _find_min_balance(self, btc_amount, coin_amount, to_exchange_coin_bid):
        coin_to_btc_price = coin_amount * to_exchange_coin_bid

        if btc_amount < coin_to_btc_price:
            result = btc_amount / coin_to_btc_price
            return btc_amount, result
        else:
            return coin_to_btc_price, coin_amount


if __name__ == '__main__':
    st = Monitoring(TEST_USER, 'Upbit', 'Binance')
    st.run()

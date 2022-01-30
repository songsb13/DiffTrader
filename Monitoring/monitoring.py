from DiffTrader.Util.utils import get_exchanges, subscribe_redis, get_min_profit, set_redis
from DiffTrader.GlobalSetting.settings import PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY, RedisKey

from multiprocessing import Process

from Exchanges.settings import Consts

from decimal import Decimal

import asyncio
import time
import json
import datetime

from Util.pyinstaller_patch import debugger


class Monitoring(Process):
    def __init__(self, user, primary_str, secondary_str):
        super(Monitoring, self).__init__()
        self._user = user
        self._exchanges = get_exchanges()

        self._primary = self._exchanges[primary_str]
        self._secondary = self._exchanges[secondary_str]

        self._primary_subscriber = subscribe_redis(primary_str)
        self._secondary_subscriber = subscribe_redis(secondary_str)

    def run(self) -> None:
        while True:
            primary_information_raw = self._primary_subscriber.get_message()
            secondary_information_raw = self._secondary_subscriber.get_message()

            if not primary_information_raw or not secondary_information_raw:
                time.sleep(1)
                continue

            primary_information = json.loads(primary_information_raw)
            secondary_information = json.loads(secondary_information_raw)

            sai_symbol_intersection = set(
                primary_information['sai_symbol_set']
            ).intersection(secondary_information['sai_symbol_set'])

            loop = asyncio.new_event_loop()
            orderbook_success, total_orderbooks = loop.run_until_complete(self._compare_orderbook(sai_symbol_intersection))

            if not orderbook_success:
                continue

            profit_dict = self._get_max_profit(primary_information, secondary_information, sai_symbol_intersection, total_orderbooks)
            if not profit_dict:
                debugger.debug()
                continue

            if profit_dict['btc_profit'] >= get_min_profit():
                set_redis(RedisKey.TradingInformation, profit_dict)

    async def _compare_orderbook(self, sai_symbol_intersection, default_btc=1):
        primary_result, secondary_result = await asyncio.gather(
            self._primary.get_curr_avg_orderbook(sai_symbol_intersection, default_btc),
            self._secondary.get_curr_avg_orderbook(sai_symbol_intersection, default_btc)
        )

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
            return False, error_message

    def _get_max_profit(self, primary_information, secondary_information, sai_symbol_intersection, total_orderbooks):
        profit_dict = dict()
        for exchange_running_type in [PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY]:
            for sai_symbol in sai_symbol_intersection:
                market, coin = sai_symbol.split('_')

                if not primary_information['balance'].get(coin):
                    # todo add log
                    pass

                elif not secondary_information['balance'].get(coin):
                    # todo add log
                    pass

                expect_profit_percent = total_orderbooks['expected_profit_dict'][exchange_running_type][sai_symbol]

                if expect_profit_percent < get_min_profit():
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
                tradable_btc, coin_amount, btc_profit = self._get_expectation(
                    expectation_data,
                    expect_profit_percent,
                    sai_symbol,
                )

                debugger.debug()

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
                            'real_difference': '',
                            'created_time': datetime.datetime.now(),
                            'primary': self._primary.name,
                            'secondary': self._secondary.name,
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

        return tradable_btc, alt_amount, btc_profit

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


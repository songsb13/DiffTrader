from DiffTrader.Util.utils import get_exchanges, get_redis, subscribe_redis
from DiffTrader.GlobalSetting.settings import PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY, RedisKey

from multiprocessing import Process

from Exchanges.settings import Consts

from decimal import Decimal, ROUND_DOWN

import asyncio
import time
import json


class Monitoring(Process):
    def __init__(self, primary_str, secondary_str):
        super(Monitoring, self).__init__()
        self._exchanges = get_exchanges()

        self._primary = self._exchanges[primary_str]
        self._secondary = self._exchanges[secondary_str]

        self._primary_subscriber = subscribe_redis(primary_str)
        self._secondary_subscriber = subscribe_redis(secondary_str)

    def run(self) -> None:
        exchange_dict = None
        while True:
            primary_information_raw = self._primary_subscriber.get_message()
            secondary_information_raw = self._secondary_subscriber.get_message()

            if not primary_information_raw or not secondary_information_raw:
                time.sleep(1)
                continue

            primary_information = json.loads(primary_information_raw)
            secondary_information = json.loads(secondary_information_raw)

            self._compare_orderbook(primary_information, secondary_information)
            self._get_max_profit(primary_information, secondary_information)

    def _get_max_profit(self, primary_information, secondary_information):
        sai_symbol_intersection = set(
            primary_information['sai_symbol_set']
        ).intersection(secondary_information['sai_symbol_set'])

        for exchange_running_type in [PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY]:
            for sai_symbol in sai_symbol_intersection:
                market, coin = sai_symbol.split('_')

                if not primary_information['balance'].get(coin):
                    # todo add log
                    pass

                elif not secondary_information['balance'].get(coin):
                    # todo add log
                    pass

    def _find_min_balance(self, btc_amount, alt_amount, alt_price, alt_precision):
        """
            calculating amount to btc_amount from from_object
            calculating amount to alt_amount from to_object

            Args:
                btc_amount: BTC amount from from_object
                alt_amount: ALT amount from to_object
                alt_price: symbol's bids
                alt_precision: precision of ALT
        """
        btc_amount = float(btc_amount)
        alt_btc = float(alt_amount) * float(alt_price['bids'])

        if btc_amount < alt_btc:
            # from_object에 있는 BTC보다 to_object에서 alt를 판매할 때 나오는 btc의 수량이 더 높은경우
            alt_amount = Decimal(float(btc_amount) / float(alt_price['bids'])).quantize(Decimal(10) ** alt_precision,
                                                                                        rounding=ROUND_DOWN)
            return btc_amount, alt_amount
        else:
            # from_object에 있는 BTC의 수량이 to_object에서 alt를 판매할 때 나오는 btc의 수량보다 더 높은경우
            alt_amount = Decimal(float(alt_amount)).quantize(Decimal(10) ** alt_precision, rounding=ROUND_DOWN)
            return alt_btc, alt_amount

    # async def _compare_orderbook(self, primary_information, secondary_information):
    #     """
    #         A -> B
    #         A -> C
    #         B -> C
    #     """
    #     exchanges = list(exchange_dict.values())
    #     total_task = list()
    #
    #     orderbook_task_result = list()
    #     for exchange in exchanges:
    #         orderbook_task = asyncio.create_task(exchange.get_curr_avg_orderbook(
    #             user_information['sai_symbol_list'],
    #             user_information['default_btc']
    #         ))
    #         result = await orderbook_task
    #         orderbook_task_result.append(result)
    #
    #     for primary in exchanges:
    #         for secondary in exchanges[1:]:
    #             task = asyncio.create_task(self._create_orderbook_task(
    #                 primary,
    #                 secondary,
    #                 user_information['sai_symbol_list'],
    #                 user_information['default_btc']
    #             ))
    #             exchange_result = await task
    #             total_task.append(exchange_result)

    async def _create_orderbook_task(self, primary, secondary, sai_symbol_list, default_btc):
        primary_result, secondary_result = await asyncio.gather(
            primary.get_curr_avg_orderbook(
                sai_symbol_list,
                default_btc
            ),
            secondary.get_curr_avg_orderbook(
                sai_symbol_list,
                default_btc
            )
        )
        success = (primary_result.success, secondary_result.success)
        wait_time = max(primary_result.wait_time, secondary_result.wait_time)

        if success:
            primary_to_secondary = dict()
            secondary_to_primary = dict()
            for sai_symbol in sai_symbol_list:
                primary_ask = primary_result.data[sai_symbol][Consts.ASKS]
                secondary_bid = secondary_result.data[sai_symbol][Consts.BIDS]
                primary_to_secondary[sai_symbol] = float(((secondary_bid - primary_ask) / primary_ask).quantize(Decimal(10) ** -8))

                primary_bid = primary_result.data[sai_symbol][Consts.BIDS]
                secondary_ask = secondary_result[sai_symbol][Consts.ASKS]
                secondary_to_primary[sai_symbol] = float(((primary_bid - secondary_ask) / secondary_ask).quantize(Decimal(10) ** -8))

            res = primary_result.data, secondary_result.data, {Consts.PRIMARY_TO_SECONDARY: primary_to_secondary,
                                                               Consts.SECONDARY_TO_PRIMARY: secondary_to_primary}

            return True, res

        else:
            time.sleep(wait_time)
            error_message = '\n'.join([primary_result.message, secondary_result.message])
            return False, error_message

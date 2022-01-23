from DiffTrader.Util.utils import get_exchanges, get_redis
from DiffTrader.GlobalSetting.settings import PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY, RedisKey

from Exchanges.settings import Consts

from decimal import Decimal, ROUND_DOWN

import asyncio
import time


class Monitoring(object):
    def monitoring(self):
        latest_user_information = None
        exchange_dict = None
        while True:
            user_information = get_redis(RedisKey.UserInformation)
            if not user_information and not latest_user_information:
                continue
            if exchange_dict is None:
                exchange_dict = get_exchanges()
            latest_user_information = user_information
            self._compare_orderbook(user_information, exchange_dict)
            self._get_max_profit(latest_user_information)

    def _get_max_profit(self, user_information):
        exchange_name_set = user_information['exchange_name_set']
        for exchange_running_type in [PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY]:
            for sai_symbol in user_information['sai_symbol_set']:
                market, coin = sai_symbol.split('_')

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

    async def _compare_orderbook(self, user_information, exchange_dict):
        """
            A -> B
            A -> C
            B -> C
        """
        exchanges = list(exchange_dict.values())
        total_task = list()

        orderbook_task_result = list()
        for exchange in exchanges:
            orderbook_task = asyncio.create_task(exchange.get_curr_avg_orderbook(
                user_information['sai_symbol_list'],
                user_information['default_btc']
            ))
            result = await orderbook_task
            orderbook_task_result.append(result)

        for primary in exchanges:
            for secondary in exchanges[1:]:
                task = asyncio.create_task(self._create_orderbook_task(
                    primary,
                    secondary,
                    user_information['sai_symbol_list'],
                    user_information['default_btc']
                ))
                total_task.append(task)

    async def _create_orderbook_task(self, primary, secondary, sai_symbol_list, default_btc):
        orderbook_task_list = list()
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
        else:
            time.sleep(wait_time)
from DiffTrader.Util.utils import get_exchanges, get_redis
from DiffTrader.GlobalSetting.settings import PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY, RedisKey

from decimal import Decimal, ROUND_DOWN


class Monitoring(object):
    def monitoring(self):
        latest_user_information = None
        while True:
            user_information = get_redis(RedisKey.UserInformation)
            if not user_information and not latest_user_information:
                continue

            latest_user_information = user_information

    def _get_max_profit(self, user_information):
        exchange_name_set = user_information['exchange_name_set']
        exchange_dict = get_exchanges()
        for exchange_running_type in [PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY]:
            for sai_symbol in user_information['sai_symbol_set']:
                market, coin = sai_symbol.split('_')

    def find_min_balance(self, btc_amount, alt_amount, alt_price, alt_precision):
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

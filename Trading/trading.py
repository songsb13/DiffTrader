from Exchanges.upbit.upbit import BaseUpbit
from Exchanges.binance.binance import Binance
from Exchanges.bithumb.bithumb import BaseBithumb
from Exchanges.settings import *
from DiffTrader.Util.utils import get_exchanges, FunctionExecutor, set_redis, get_redis
from DiffTrader.GlobalSetting.settings import *
from Util.pyinstaller_patch import *


class Trading(object):
    """
        monitoring process에서 넘어온 각종 이벤트 값들에 대한 트레이딩 시도
        High Priority

    """

    def checking_order(self, exchange, order_id, **additional):
        for _ in range(10):
            result = exchange.get_order_history(order_id, additional)

            if result.success and result.data['sai_status'] == SaiOrderStatus.CLOSED:
                return result.data
            time.sleep(1)

    def _trade(self, from_exchange, to_exchange, profit_information):
        """
            from_exchange: A object that will be buying the ALT coin
            to_exchange: A object that will be selling the ALT coin
        """
        market, coin = profit_information['sai_symbol'].split('_')[1]

        with FunctionExecutor(from_exchange.base_to_alt) as executor:
            from_result = executor.loop_executor(
                profit_information['sai_symbol'],
                profit_information['tradable_btc'],
                profit_information['coin_amount'],
                profit_information['from_object_trading_fee'],
                profit_information['to_object_trading_fee']
            )
            if not from_result:
                debugger.debug()
                return False

            buy_check_result = self.checking_order(
                from_exchange,
                from_result.data['sai_order_id'],
                symbol=profit_information['sai_symbol']
            )

        from_exchange_coin_price = buy_check_result['sai_average_price']
        from_exchange_coin_amount = buy_check_result['sai_amount']

        with FunctionExecutor(to_exchange.alt_to_base) as executor:
            to_result = executor.loop_executor(
                profit_information['sai_symbol'],
                profit_information['tradable_btc'],
                from_exchange_coin_amount
            )

            sell_check_result = self.checking_order(
                to_exchange,
                to_result.data['sai_order_id'],
                symbol=profit_information['sai_symbol']
            )

            if not to_result:
                debugger.debug()
                return False

        to_exchange_coin_price = buy_check_result['sai_average_price']
        to_exchange_coin_amount = sell_check_result['sai_amount']

        trading_information = dict(
            from_exchange=dict(
                price=from_exchange_coin_price,
                amount=from_exchange_coin_amount
            ),
            to_exchange=dict(
                price=to_exchange_coin_price,
                amount=to_exchange_coin_amount
            )
        )
        return trading_information

    def trading(self):
        while True:
            profit_information = get_redis('profit_information')

            if not profit_information:
                continue

            primary_str, secondary_str = profit_information['primary_str'], profit_information['secondary_str']
            exchange_dict = get_exchanges()

            if profit_information['trade_type'] == PRIMARY_TO_SECONDARY:
                trading_information = self._trade(exchange_dict[primary_str],
                                                  exchange_dict[secondary_str],
                                                  profit_information)
            else:
                trading_information = self._trade(exchange_dict[secondary_str],
                                                  exchange_dict[primary_str],
                                                  profit_information)

            debugger.debug('trading information: [{}]'.format(trading_information))
            if trading_information is None:
                raise

            set_redis('trading_information', trading_information)

            time.sleep(0.1)

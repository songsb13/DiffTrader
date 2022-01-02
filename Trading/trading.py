from Exchanges.upbit.upbit import BaseUpbit
from Exchanges.binance.binance import Binance
from Exchanges.bithumb.bithumb import BaseBithumb
from Exchanges.settings import *
from DiffTrader.Util.utils import get_exchanges, FunctionExecutor
from DiffTrader.GlobalSetting.settings import *
from Util.pyinstaller_patch import *


class Trading(object):
    """
        monitoring process에서 넘어온 각종 이벤트 값들에 대한 트레이딩 시도
        High Priority

    """
    def __init__(self, primary_str, secondary_str, profit_information):
        self._primary_str = primary_str
        self._secondary_str = secondary_str
        self._profit_information = profit_information

    def checking_order(self, exchange, order_id, **additional):
        for _ in range(10):
            result = exchange.get_order_history(order_id, additional)

            if result.success and result.data['sai_status'] == SaiOrderStatus.CLOSED:
                return result.data
            time.sleep(3)

    def _trade(self, from_exchange, to_exchange):
        """
            from_exchange: A object that will be buying the ALT coin
            to_exchange: A object that will be selling the ALT coin
        """
        market, coin = self._profit_information['sai_symbol'].split('_')[1]

        if self._profit_information['']:
            pass

        with FunctionExecutor(from_exchange.base_to_alt) as executor:
            from_result = executor.loop_executor(
                self._profit_information['sai_symbol'],
                self._profit_information['tradable_btc'],
                self._profit_information['coin_amount'],
                self._profit_information['from_object_trading_fee'],
                self._profit_information['to_object_trading_fee']
            )
            if not from_result:
                debugger.debug()
                return False

            buy_check_result = self.checking_order(
                from_exchange,
                from_result.data['sai_order_id'],
                symbol=self._profit_information['sai_symbol']
            )

        from_exchange_coin_price = buy_check_result['sai_average_price']
        from_exchange_coin_amount = buy_check_result['sai_amount']

        with FunctionExecutor(to_exchange.alt_to_base) as executor:
            to_result = executor.loop_executor(
                self._profit_information['sai_symbol'],
                self._profit_information['tradable_btc'],
                from_exchange_coin_amount
            )

            sell_check_result = self.checking_order(
                to_exchange,
                to_result.data['sai_order_id'],
                symbol=self._profit_information['sai_symbol']
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

        debugger.debug('trading information: [{}]'.format(trading_information))

        return trading_information

    def trading(self):
        exchange_dict = get_exchanges()

        if self._profit_information['trade_type'] == PRIMARY_TO_SECONDARY:
            trading_information = self._trade(exchange_dict[self._primary_str], exchange_dict[self._secondary_str])
        else:
            trading_information = self._trade(exchange_dict[self._secondary_str], exchange_dict[self._primary_str])

        if trading_information is None:
            pass

        return trading_information

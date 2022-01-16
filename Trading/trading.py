import time

from Exchanges.settings import BaseTradeType, SaiOrderStatus
from DiffTrader.Util.utils import get_exchanges, get_auto_withdrawal, FunctionExecutor, set_redis, get_redis
from DiffTrader.GlobalSetting.settings import *
from DiffTrader.GlobalSetting.messages import *
from Util.pyinstaller_patch import debugger

from concurrent.futures import ThreadPoolExecutor


class Trading(object):
    """
        monitoring process에서 넘어온 각종 이벤트 값들에 대한 트레이딩 시도
        High Priority

    """

    def checking_order(self, exchange, order_id, **additional):
        debugger.debug(GlobalMessage.ENTRANCE.format(data=str(locals())))
        for _ in range(60):
            result = exchange.get_order_history(order_id, additional)

            if result.success and result.data['sai_status'] == SaiOrderStatus.CLOSED:
                return result
            time.sleep(1)
        return result

    def _trade(self, exchange, trade_func, trade_type, profit_information):
        """
            from_exchange: Exchange that will be buying the ALT coin
            to_exchange: Exchange that will be selling the ALT coin
        """
        debugger.debug(GlobalMessage.ENTRANCE.format(data=str(locals())))
        with FunctionExecutor(trade_func) as executor:
            result = executor.loop_executor(
                profit_information['sai_symbol'],
                trade_type,
                profit_information['base_to_alt_amount'],
            )
            if not result.success:
                debugger.debug(TradingMessage.Debug.FAIL_TO_TRADING.format())
                return None, None
            debugger.debug(TradingMessage.Debug.TRADING_RESULT.format(result.data))

        order_result = self.checking_order(
            exchange,
            result.data['sai_order_id'],
            symbol=profit_information['sai_symbol']
        )

        if not order_result:
            # 매매 실패시의 별도 시퀀스?
            pass

        exchange_coin_price = order_result['sai_average_price']
        exchange_coin_amount = order_result['sai_amount']

        return exchange_coin_price, exchange_coin_amount

    def trading(self):
        debugger.debug(GlobalMessage.ENTRANCE.format(data=str(locals())))
        thread_executor = ThreadPoolExecutor(max_workers=2)
        while True:
            profit_information = get_redis(RedisKey.ProfitInformation)

            if not profit_information:
                continue

            primary_str, secondary_str = profit_information['primary_str'], profit_information['secondary_str']
            exchange_dict = get_exchanges()

            if profit_information['trade_type'] == PRIMARY_TO_SECONDARY:
                buy_args = [exchange_dict[primary_str],
                            exchange_dict[primary_str].buy,
                            BaseTradeType.BUY_MARKET,
                            profit_information]

                sell_args = [exchange_dict[secondary_str],
                             exchange_dict[secondary_str].sell,
                             BaseTradeType.SELL_MARKET,
                             profit_information]
            else:
                buy_args = [exchange_dict[secondary_str],
                            exchange_dict[secondary_str].buy,
                            BaseTradeType.BUY_MARKET,
                            profit_information]

                sell_args = [exchange_dict[primary_str],
                             exchange_dict[primary_str].sell,
                             BaseTradeType.SELL_MARKET,
                             profit_information]

            from_exchange_coin_price, from_exchange_coin_amount = thread_executor.submit(self._trade, *buy_args)
            to_exchange_coin_price, to_exchange_coin_amount = thread_executor.submit(self._trade, *sell_args)

            trading_information = dict(
                from_exchange=dict(
                    name=primary_str,
                    price=from_exchange_coin_price,
                    amount=from_exchange_coin_amount
                ),
                to_exchange=dict(
                    name=secondary_str,
                    price=to_exchange_coin_price,
                    amount=to_exchange_coin_amount
                )
            )

            debugger.debug(TradingMessage.Debug.TRADING_INFORMATION)
            if trading_information is None:
                debugger.debug(TradingMessage.Debug.INFORMATION_NOT_FOUND)
                raise

            if get_auto_withdrawal():
                set_redis(RedisKey.TradingInformation, trading_information)

            time.sleep(0.1)

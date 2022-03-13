import time
import json
from Exchanges.settings import BaseTradeType, SaiOrderStatus, Consts
from DiffTrader.Util.utils import get_exchanges, get_auto_withdrawal, FunctionExecutor, set_redis, get_redis, DecimalDecoder
from DiffTrader.GlobalSetting.settings import *
from DiffTrader.GlobalSetting.test_settings import *
from DiffTrader.GlobalSetting.messages import *
from Util.pyinstaller_patch import debugger

from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process


class Trading(Process):
    """
        monitoring process에서 넘어온 각종 이벤트 값들에 대한 트레이딩 시도
        High Priority
    """

    def __init__(self):
        super(Trading, self).__init__()

    def run(self) -> None:
        debugger.debug(GlobalMessage.ENTRANCE.format(data=str(locals())))
        thread_executor = ThreadPoolExecutor(max_workers=2)
        exchange_dict = get_exchanges()
        while True:
            if not DEBUG:
                profit_information = get_redis(RedisKey.ProfitInformation, use_decimal=True)

                if not profit_information:
                    continue
            else:
                profit_information = json.loads(TRADING_TEST_INFORMATION, cls=DecimalDecoder)

            primary_str, secondary_str = (profit_information['additional_information']['primary'],
                                          profit_information['additional_information']['secondary'])

            if profit_information['exchange_running_type'] == PRIMARY_TO_SECONDARY:
                buy_args = [exchange_dict[primary_str],
                            exchange_dict[primary_str].buy,
                            BaseTradeType.BUY_MARKET,
                            profit_information,
                            profit_information['additional_information']['sai_symbol'],
                            profit_information['additional_information']['coin_amount'],
                            profit_information['additional_information']['total_orderbooks'][primary_str][Consts.ASKS]]

                sell_args = [exchange_dict[secondary_str],
                             exchange_dict[secondary_str].sell,
                             BaseTradeType.SELL_MARKET,
                             profit_information,
                             profit_information['additional_information']['sai_symbol'],
                             profit_information['additional_information']['sell_coin_amount'],
                             profit_information['additional_information']['total_orderbooks'][secondary_str][Consts.BIDS]]
            else:
                buy_args = [exchange_dict[secondary_str],
                            exchange_dict[secondary_str].buy,
                            BaseTradeType.BUY_MARKET,
                            profit_information,
                            profit_information['additional_information']['sai_symbol'],
                            profit_information['additional_information']['coin_amount'],
                            profit_information['additional_information']['total_orderbooks'][secondary_str][Consts.ASKS]]

                sell_args = [exchange_dict[primary_str],
                             exchange_dict[primary_str].sell,
                             BaseTradeType.SELL_MARKET,
                             profit_information,
                             profit_information['additional_information']['sai_symbol'],
                             profit_information['additional_information']['sell_coin_amount'],
                             profit_information['additional_information']['total_orderbooks'][primary_str][Consts.BIDS]]

            buy_executor = thread_executor.submit(self._trade, *buy_args)
            sell_executor = thread_executor.submit(self._trade, *sell_args)

            from_exchange_coin_price, from_exchange_coin_amount = buy_executor.result()
            to_exchange_coin_price, to_exchange_coin_amount = sell_executor.result()

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

            send_information = {**trading_information, **dict(full_url_path=SaiUrls.BASE + SaiUrls.TRADING)}
            set_redis(RedisKey.SendInformation, send_information)

            time.sleep(0.1)

    def checking_order(self, exchange, order_id, **additional):
        debugger.debug(GlobalMessage.ENTRANCE.format(data=str(locals())))
        for _ in range(60):
            result = exchange.get_order_history(order_id, additional)

            if result.success and result.data['sai_status'] == SaiOrderStatus.CLOSED:
                return result
            time.sleep(1)
        return result

    def _trade(self, exchange, trade_func, trade_type, sai_symbol, coin_amount, price):
        """
            from_exchange: Exchange that will be buying the ALT coin
            to_exchange: Exchange that will be selling the ALT coin
        """
        debugger.debug(GlobalMessage.ENTRANCE.format(data=str(locals())))
        with FunctionExecutor(trade_func) as executor:
            result = executor.loop_executor(
                sai_symbol,
                trade_type,
                coin_amount,
                price
            )
            if not result.success:
                debugger.debug(TradingMessage.Debug.FAIL_TO_TRADING.format())
                return None, None
            debugger.debug(TradingMessage.Debug.TRADING_RESULT.format(result.data))

        order_result = self.checking_order(
            exchange,
            result.data['sai_order_id'],
            symbol=sai_symbol
        )

        if not order_result:
            # 매매 실패시의 별도 시퀀스?
            pass

        exchange_coin_price = order_result['sai_average_price']
        exchange_coin_amount = order_result['sai_amount']

        return exchange_coin_price, exchange_coin_amount


if __name__ == '__main__':
    trading = Trading()
    trading.run()
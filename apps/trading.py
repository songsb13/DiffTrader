"""
    목적
        1. Monitoring Process로부터 받은 profit data를 바탕으로 거래를 진행한다.
        2. 매매 완료가 되었는지 파악하고, 결과 값을 withdrawal process로 보낸다.

    기타
        1. 발생하는 Process의 수는 하나이다.
        2. 해당 process는 2개의 thread를 가지고, 각 거래소1의 매수거래, 거래소2의 매도거래를 진행한다.
        3. 해당 프로세스의 완료 시점은 매매가 완료되어 withdrawal domain으로 결과 값이 보내지는 시점이다.
        4. 해당 process는 가장 높은 우선순위를 가지고 있으므로, api_process를 통해 명령을 보내지 않고 직접 실행한다.
"""
import time
import json
import logging.config

from Exchanges.settings import BaseTradeType, SaiOrderStatus, Consts
from DiffTrader.utils.util import get_exchanges, get_auto_withdrawal, FunctionExecutor, set_redis, get_redis, DecimalDecoder
from DiffTrader.settings.base import RedisKey, SaiUrls, DEBUG, TraderConsts
from DiffTrader.settings.test_settings import *
from DiffTrader.settings.message import CommonMessage as CMsg
from DiffTrader.settings.message import TradingMessage as TMsg
from DiffTrader.utils.logger import SetLogger

from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process

__file__ = 'trading.py'


logging_config = SetLogger.get_config_base_process(__file__)
logging.config.dictConfig(logging_config)


class Trading(Process):

    def __init__(self):
        super(Trading, self).__init__()

    def run(self) -> None:
        logging.info(CMsg.START)
        thread_executor = ThreadPoolExecutor(max_workers=2)
        exchange_dict = get_exchanges()
        while True:
            if not DEBUG:
                profit_information = get_redis(RedisKey.ProfitInformation, use_decimal=True)
                if not profit_information:
                    logging.debug(TMsg.Debug.WAIT_INFORMATION)
                    time.sleep(0.5)
                    continue
            else:
                profit_information = json.loads(TRADING_TEST_INFORMATION, cls=DecimalDecoder)

            from_exchange_str, to_exchange_str = (profit_information['additional_information']['from_exchange'],
                                                  profit_information['additional_information']['to_exchange'])

            sai_symbol = profit_information['sai_symbol']
            if profit_information['exchange_running_type'] == TraderConsts.PRIMARY_TO_SECONDARY:
                buy_args = [exchange_dict[from_exchange_str],
                            exchange_dict[from_exchange_str].buy,
                            BaseTradeType.BUY_MARKET,
                            sai_symbol,
                            profit_information['coin_amount'],
                            profit_information['additional_information']['total_orderbooks']['primary'][sai_symbol][Consts.ASKS]]

                sell_args = [exchange_dict[to_exchange_str],
                             exchange_dict[to_exchange_str].sell,
                             BaseTradeType.SELL_MARKET,
                             sai_symbol,
                             profit_information['sell_coin_amount'],
                             profit_information['additional_information']['total_orderbooks']['secondary'][sai_symbol][Consts.BIDS]]
            else:
                buy_args = [exchange_dict[to_exchange_str],
                            exchange_dict[to_exchange_str].buy,
                            BaseTradeType.BUY_MARKET,
                            sai_symbol,
                            profit_information['coin_amount'],
                            profit_information['additional_information']['total_orderbooks']['secondary'][sai_symbol][Consts.ASKS]]

                sell_args = [exchange_dict[from_exchange_str],
                             exchange_dict[from_exchange_str].sell,
                             BaseTradeType.SELL_MARKET,
                             sai_symbol,
                             profit_information['sell_coin_amount'],
                             profit_information['additional_information']['total_orderbooks']['primary'][sai_symbol][Consts.BIDS]]

            tasks = []
            for args in [buy_args, sell_args]:
                task = thread_executor.submit(self._trade, *args)
                tasks.append(task)

            from_price, from_amount = tasks[0].result()
            to_price, to_amount = tasks[1].result()

            trading_information = {
                'from_exchange': {
                    'name': from_exchange_str,
                    'price': from_price,
                    'amount': from_amount
                },
                'to_exchange': {
                    'name': to_exchange_str,
                    'price': to_price,
                    'amount': to_amount
                }
            }
            logging.debug(TMsg.Debug.TRADING_INFORMATION.format(trading_information))
            if trading_information is None:
                logging.debug(TMsg.Debug.INFORMATION_NOT_FOUND)
                raise

            if get_auto_withdrawal():
                set_redis(RedisKey.TradingInformation, trading_information, use_decimal=True)

            send_information = {**trading_information, **dict(full_url_path=SaiUrls.BASE + SaiUrls.TRADING)}
            set_redis(RedisKey.SendInformation, send_information, use_decimal=True)

            time.sleep(0.1)

    def _trade(self, exchange, trade_func, trade_type, sai_symbol, coin_amount, price):
        """
            from_exchange: Exchange that will be buying the ALT coin
            to_exchange: Exchange that will be selling the ALT coin
        """
        logging.debug(CMsg.entrance_with_parameter(
            self._trade,
            (exchange, trade_func, trade_type, sai_symbol, coin_amount, price)
        ))
        with FunctionExecutor(trade_func) as executor:
            result = executor.loop_executor(
                sai_symbol,
                trade_type,
                coin_amount,
                price
            )
            if not result.success:
                logging.debug(TMsg.Debug.FAIL_TO_TRADING.format(result.message))
                return None, None
            logging.debug(TMsg.Debug.TRADING_RESULT.format(result.data))

        if result.data['sai_order_id'] in "DEBUG-TEST-ID":
            return result.data['sai_average_price'], result.data['sai_amount']

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

    def checking_order(self, exchange, order_id, **additional):
        logging.debug(CMsg.entrance_with_parameter(
            self.checking_order,
            (exchange, order_id, additional)
        ))
        for _ in range(60):
            result = exchange.get_order_history(order_id, additional)

            if result.success and result.data['sai_status'] == SaiOrderStatus.CLOSED:
                return result
            time.sleep(1)
        return result


if __name__ == '__main__':
    trading = Trading()
    trading.run()
"""
    thread for calculating & trading & withdrawing two exchanges
"""

# Python Inner parties
import time
import asyncio

from decimal import Decimal, ROUND_DOWN
from datetime import datetime

# SAI parties
from Exchanges.Bithumb.bithumb import Bithumb
from Exchanges.Binance.binance import Binance
# from Exchanges.Bitfinex.bitfinex import Bitfinex
from Exchanges.Upbit.upbit import BaseUpbit
# from Exchanges.Huobi.huobi import Huobi

from Util.pyinstaller_patch import *
# END

# Domain parties
from DiffTrader.apps.trading.messages import (Logs, Messages as Msg)
from DiffTrader.apps.trading.threads.settings import (TAG_COINS, PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY,
                                                      ONE_WAY_EXCHANGES)

# Third parties
from PyQt5.QtCore import pyqtSignal, QThread


"""
    모든 함수 값에 self가 있으면, self를 우선순위로 둬야함
    def send(primary, secondary)
        --> 이 경우 이미 self.primary_obj.exchange가 있으므로 
    
    def send():
        self.primary_obj.exchange ... 로 처리
"""


class MaxProfits(object):
    def __init__(self, btc_profit, tradable_btc, alt_amount, currency, trade):
        """
            Profit object for comparing numerous currencies
            Args:
                btc_profit: Arbitrage profit of BTC on both exchanges
                tradable_btc: It can be BTC amount at from_object or convertible amount that ALT to BTC at to_object
                alt_amount: to_object's ALT amount
                currency: It will be a customize symbol like {MARKET}_{COIN} ( BTC_ETH )
                trade: Trade type that primary to secondary or secondary to primary.
                information: It is profit data and sending to SAI server for collecting it
        """
        self.btc_profit = btc_profit
        self.tradable_btc = tradable_btc
        self.alt_amount = alt_amount
        self.currency = currency
        self.trade_type = trade

        self.information = None


class ExchangeInfo(object):
    # todo primary_info는 diff_trader에 받고있는데, 하나의 DICT에 하나의 거래소만 받는데 왜 dict처리하는지 확인 필요함.
    """
        Exchange object for setting exchange's information like name, balance, fee and etc.
    """
    def __init__(self, cfg, name, log):
        # todo property, setter의 사용성에 대해 재고가 필요, 만약에 변수들에 대한 처리가 많아야 하는 경우에는 필요할듯.
        self._log = log
        self.__cfg = cfg
        self.__name = None
        self.__name = name

        self.__exchange = None

        self.__balance = None
        self.__orderbook = None
        self.__td_fee = None
        self.__tx_fee = None
        self.__deposit = None

        self.__fee_cnt = None

    @property
    def cfg(self):
        return self.__cfg

    @cfg.setter
    def cfg(self, val):
        self.__cfg = val

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, val):
        self.__name = val

    @property
    def exchange(self):
        return self.__exchange

    @exchange.setter
    def exchange(self, val):
        self.__exchange = val

    @property
    def balance(self):
        return self.__balance

    @balance.setter
    def balance(self, val):
        self.__balance = val

    @property
    def orderbook(self):
        return self.__orderbook

    @orderbook.setter
    def orderbook(self, val):
        self.__orderbook = val

    @property
    def trading_fee(self):
        return self.__td_fee

    @trading_fee.setter
    def trading_fee(self, val):
        self.__td_fee = val

    @property
    def transaction_fee(self):
        return self.__tx_fee

    @transaction_fee.setter
    def transaction_fee(self, val):
        self.__tx_fee = val

    @property
    def fee_cnt(self):
        return self.__fee_cnt

    @fee_cnt.setter
    def fee_cnt(self, val):
        self.__fee_cnt = val

    @property
    def deposit(self):
        return self.__deposit

    @deposit.setter
    def deposit(self, val):
        self.__deposit = val


class TradeThread(QThread):
    log_signal = pyqtSignal(int, str)
    stopped = pyqtSignal()
    profit_signal = pyqtSignal(str, float)

    def __init__(self, email, primary_info, secondary_info, min_profit_per, min_profit_btc, auto_withdrawal):
        """
            Thread for calculating the profit and sending coins between primary exchange and secondary exchange.
            Args:
                email: user's email
                primary_info: Primary exchange's information, key, secret and etc
                secondary_info: Secondary exchange's information, key, secret and etc
                min_profit_btc: Minimum BTC profit config
                min_profit_per: Minimum profit percent config
                auto_withdrawal: auto withdrawal config
        """
        super().__init__()
        self.stop_flag = True
        self.log = Logs(self.log_signal)
        self.email = email
        self.min_profit_per = min_profit_per
        self.min_profit_btc = min_profit_btc
        self.auto_withdrawal = auto_withdrawal

        self.primary_obj = ExchangeInfo(cfg=primary_info, name=list(primary_info.keys())[0], log=self.log)
        self.secondary_obj = ExchangeInfo(cfg=secondary_info, name=list(secondary_info.keys())[0], log=self.log)

        self.collected_data = dict()
        self.currencies = None

    def stop(self):
        self.stop_flag = True

    def run(self):
        list_ = list()
        for info in [self.primary_obj, self.secondary_obj]:
            list_.append(self.get_exchange(info.name, info.cfg))
        else:
            self.primary_obj.exchange, self.secondary_obj.exchange = list_

        if not self.primary_obj.exchange or not self.secondary_obj.exchange:
            self.stop()
            self.stopped.emit()
            return

        self.stop_flag = False
        try:
            self.min_profit_per /= 100.0
            self.log.send(Msg.Init.MIN_PROFIT.format(min_profit=self.min_profit_per))
            self.log.send(Msg.Init.MIN_BTC.format(min_btc=self.min_profit_btc))
            self.log.send(Msg.Init.AUTO.format(auto_withdrawal=self.auto_withdrawal))
        except:
            self.log.send(Msg.Init.WRONG_INPUT)
            self.stop()
            self.stopped.emit()
            return

        self.log.send(Msg.Init.START)

        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.trader())
        loop.close()

        self.stop()
        self.stopped.emit()

    async def trader(self):
        try:
            if self.auto_withdrawal:
                self.log.send(Msg.Init.GET_WITHDRAWAL_INFO)
                await self.deposits()
                self.log.send(Msg.Init.SUCCESS_WITHDRAWAL_INFO)

            fee_refresh_time = int()
            while evt.is_set() and not self.stop_flag:
                try:
                    if time.time() >= fee_refresh_time + 600:
                        tx_res = await self.get_transaciton_fees()
                        td_res = await self.get_trading_fees()

                        if not (tx_res and td_res):
                            continue

                        self.log.send(Msg.Trade.SUCCESS_FEE_INFO)
                        fee_refresh_time = time.time()
                    is_success = await self.balance_and_currencies()
                    if not is_success:
                        continue
                    if not self.currencies:
                        # Intersection 결과가 비어있는 경우
                        self.log.send(Msg.Trade.NO_AVAILABLE)
                        continue

                    primary_btc = self.primary_obj.balance.get('BTC', 0)
                    secondary_btc = self.secondary_obj.balance.get('BTC', 0)

                    default_btc = max(primary_btc, secondary_btc) * 1.5

                    if not default_btc:
                        # BTC가 balance에 없는 경우
                        self.log.send(Msg.Trade.NO_BALANCE_BTC)
                        continue

                    success, data, error, time_ = await self.compare_orderbook(default_btc)
                    if not success:
                        self.log.send(Msg.Trade.ERROR_CONTENTS.format(error_string=error))
                        time.sleep(time_)
                        continue

                    profit_object = self.get_max_profit(data)
                    if not profit_object:
                        self.log.send(Msg.Trade.NO_PROFIT)
                        continue
                    if profit_object.btc_profit >= self.min_profit_btc:
                        try:
                            trade_success = self.trade(profit_object)
                            send_expected_profit(profit_object)

                            if not trade_success:
                                self.log.send(Msg.Trade.FAIL)
                                continue
                            self.log.send(Msg.Trade.SUCCESS)

                        except:
                            debugger.exception(Msg.Error.EXCEPTION)
                            self.log.send_error(Msg.Error.EXCEPTION)
                            send_expected_profit(profit_object)

                            return False
                    else:
                        self.log.send(Msg.Trade.NO_MIN_BTC)
                        send_expected_profit(profit_object)

                except:
                    debugger.exception(Msg.Error.EXCEPTION)
                    self.log.send_error(Msg.Error.EXCEPTION)
                    return False

            return True
        except:
            debugger.exception(Msg.Error.EXCEPTION)
            self.log.send_error(Msg.Error.EXCEPTION)
            return False

    def get_exchange(self, exchange_str, cfg):
        if exchange_str == 'Bithumb':
            return Bithumb(cfg['key'], cfg['secret'])
        elif exchange_str == 'Binance':
            exchange = Binance(cfg['key'], cfg['secret'])
            exchange.get_exchange_info()
            return exchange
        elif exchange_str == 'Bitfinex':
            return Bitfinex(cfg['key'], cfg['secret'])
        elif exchange_str.startswith('Upbit'):
            # todo 차후 리팩토링에서 수정 예정임
            return BaseUpbit(cfg['key'], cfg['secret'])
        elif exchange_str == 'Huobi':
            exchange = Huobi(cfg['key'], cfg['secret'])
            exchange.get_account_id()
            return exchange

    @loop_wrapper(debugger=debugger)
    async def deposits(self):
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.get_deposit_addrs(), self.secondary_obj.exchange.get_deposit_addrs()
        )
        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            return None

        self.primary_obj.deposit = primary_res.data
        self.secondary_obj.deposit = secondary_res.data

        return True

    @loop_wrapper(debugger=debugger)
    async def get_trading_fees(self):
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.get_trading_fee(),
            self.secondary_obj.exchange.get_trading_fee(),
        )

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            return None

        self.primary_obj.trading_fee = primary_res.data
        self.secondary_obj.trading_fee = secondary_res.data

        return True

    @loop_wrapper(debugger=debugger)
    async def get_transaciton_fees(self):
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.get_transaction_fee(),
            self.secondary_obj.exchange.get_transaction_fee()
        )

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            return None

        self.primary_obj.transaction_fee = primary_res.data
        self.secondary_obj.transaction_fee = secondary_res.data

        return True

    def get_precision(self, currency):
        primary_res = self.primary_obj.exchange.get_precision(currency)
        secondary_res = self.secondary_obj.exchange.get_precision(currency)

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            return None

        primary_btc_precision, primary_alt_precision = primary_res.data
        secondary_btc_precision, secondary_alt_precision = secondary_res.data

        btc_precision = max(primary_btc_precision, secondary_btc_precision)
        alt_precision = max(secondary_btc_precision, secondary_alt_precision)

        return btc_precision, alt_precision

    @loop_wrapper(debugger=debugger)
    async def balance_and_currencies(self):
        """
            All balance values require type int, float.
        """
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.balance(),
            self.secondary_obj.exchange.balance()
        )

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            return None

        self.primary_obj.balance = primary_res.data
        self.secondary_obj.balance = secondary_res.data

        self.currencies = list(set(self.secondary_obj.balance).intersection(self.primary_obj.balance))

        return True

    @loop_wrapper(debugger=debugger)
    async def compare_orderbook(self, default_btc=1.0):
        """
            It is for getting arbitrage profit primary to secondary or secondary to primary.
        """
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.get_curr_avg_orderbook(self.currencies, default_btc),
            self.secondary_obj.exchange.get_curr_avg_orderbook(self.currencies, default_btc)
        )

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            return None

        primary_to_secondary = dict()
        for currency_pair in self.currencies:
            primary_ask = primary_res.data[currency_pair]['asks']
            secondary_bid = secondary_res.data[currency_pair]['bids']
            primary_to_secondary[currency_pair] = float(((secondary_bid - primary_ask) / primary_ask))

        secondary_to_primary = dict()
        for currency_pair in self.currencies:
            primary_bid= primary_res.data[currency_pair]['bids']
            secondary_ask = secondary_res.data[currency_pair]['asks']
            secondary_to_primary[currency_pair] = float(((primary_bid- secondary_ask) / secondary_ask))

        res = primary_res.data, secondary_res.data, {PRIMARY_TO_SECONDARY: primary_to_secondary,
                                                     SECONDARY_TO_PRIMARY: secondary_to_primary}

        return res

    def get_expectation_by_balance(self, from_object, to_object, currency, alt, btc_precision, alt_precision, real_diff):
        """
            Args:
                from_object: Exchange that buying the ALT
                to_object: Exchange that selling the BTC
                currency: SAI symbol, {MARKET}_{COIN}
                btc_precision: precision of BTC
                alt_precision: precision of ALT
                real_diff:
        """
        tradable_btc, alt_amount = self.find_min_balance(from_object.balance['BTC'],
                                                         to_object.balance[alt],
                                                         to_object.orderbook[currency], currency,
                                                         btc_precision, alt_precision)

        self.log.send(Msg.Trade.TRADABLE.format(
            from_exchange=from_object.name,
            to_exchange=to_object.name,
            alt=alt,
            alt_amount=alt_amount,
            tradable_btc=tradable_btc
        ))
        btc_profit = (tradable_btc * Decimal(real_diff)) - (
                Decimal(from_object.transaction_fee[alt]) * from_object.orderbook[currency]['asks']) - Decimal(
            to_object.transaction_fee['BTC'])

        self.log.send(Msg.Trade.BTC_PROFIT.format(
            from_exchange=from_object.name,
            to_exchange=to_object.name,
            alt=alt,
            btc_profit=btc_profit,
            btc_profit_per=real_diff * 100
        ))

        return tradable_btc, alt_amount, btc_profit

    def get_max_profit(self, data):
        """
            Args:
                data:
                    primary_orderbook: dict, primary orderbook for checking profit
                    secondary_orderbook: dict, secondary orderbook for checking profit
                    exchanges_coin_profit_set: dict, profit percent by currencies
        """
        profit_object = None
        primary_orderbook, secondary_orderbook, exchanges_coin_profit_set = data
        for trade in [PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY]:
            if self.primary_obj.name in ONE_WAY_EXCHANGES and trade == PRIMARY_TO_SECONDARY:
                # 특정 거래소의 경우 한 방향에서의 거래밖에 적용되지 않음.
                continue
            for currency in self.currencies:
                alt = currency.split('_')[1]
                if not self.primary_obj.balance.get(alt):
                    self.log.send(Msg.Trade.NO_BALANCE_ALT.format(exchange=self.primary_obj.name, alt=alt))
                    continue
                elif not self.secondary_obj.balance.get(alt):
                    self.log.send(Msg.Trade.NO_BALANCE_ALT.format(exchange=self.secondary_obj.name, alt=alt))
                    continue

                expect_profit_percent = data.get(trade, dict()).get(currency, int())

                if trade == PRIMARY_TO_SECONDARY and expect_profit_percent >= 0:
                    sender, receiver, asks, bids, profit_per = self.primary_obj.name, self.secondary_obj.name, \
                                                        primary_orderbook[currency]['asks'], \
                                                        secondary_orderbook[currency]['bids'], \
                                                        expect_profit_percent * 100,
                else:  # trade == SECONDARY_TO_PRIMARY and expect_profit_percent >= 0:
                    sender, receiver, asks, bids, profit_per = self.secondary_obj.name, self.primary_obj.name, \
                                                        secondary_orderbook[currency]['asks'], \
                                                        primary_orderbook[currency]['bids'], \
                                                        expect_profit_percent * 100

                self.log.send(Msg.Trade.EXCEPT_PROFIT.format(
                    from_exchange=sender,
                    to_exchange=receiver,
                    currency=currency,
                    profit_per=profit_per
                ))
                debugger.debug(Msg.Debug.ASK_BID.format(
                    currency=currency,
                    from_exchange=sender,
                    from_asks=asks,
                    to_exchange=receiver,
                    to_bids=bids
                ))

                if expect_profit_percent < self.min_profit_per:
                    continue

                primary_trade_fee_percent = (1 - self.primary_obj.trading_fee) ** self.primary_obj.fee_cnt
                secondary_trade_fee_percent = (1 - self.secondary_obj.trading_fee) ** self.secondary_obj.fee_cnt

                real_diff = ((1 + expect_profit_percent) * primary_trade_fee_percent * secondary_trade_fee_percent) - 1

                # get precision of BTC and ALT
                precision_set = self.get_precision(currency)
                if not precision_set:
                    return False
                btc_precision, alt_precision = precision_set

                try:
                    if trade == PRIMARY_TO_SECONDARY:
                        tradable_btc, alt_amount, btc_profit = self.get_expectation_by_balance(
                            self.primary_obj, self.secondary_obj, currency, alt, btc_precision, alt_precision, real_diff
                        )
                    else:
                        tradable_btc, alt_amount, btc_profit = self.get_expectation_by_balance(
                            self.secondary_obj, self.primary_obj, currency, alt, btc_precision, alt_precision, real_diff
                        )

                    debugger.debug(Msg.Debug.TRADABLE_BTC.format(tradable_btc=tradable_btc))
                    debugger.debug(Msg.Debug.TRADABLE_ASK_BID.format(
                        from_exchange=self.secondary_obj.name,
                        from_orderbook=secondary_orderbook[currency],
                        to_exchange=self.primary_obj.name,
                        to_orderbook=primary_orderbook[currency]

                    ))
                except:
                    debugger.exception(Msg.Error.FATAL)
                    continue

                if profit_object is None and (tradable_btc and alt_amount):
                    profit_object = MaxProfits(btc_profit, tradable_btc, alt_amount, currency, trade)
                elif profit_object is None:
                    continue
                elif profit_object.btc_profit < btc_profit:
                    profit_object = MaxProfits(btc_profit, tradable_btc, alt_amount, currency, trade)

                profit_object.information = dict(
                    user_id=self.email,
                    profit_percent=real_diff,
                    profit_btc=btc_profit,
                    currency_time=datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                    primary_market=self.primary_obj.name,
                    secondary_market=self.secondary_obj.name,
                    currency_name=currency
                )

        return profit_object

    @staticmethod
    def find_min_balance(btc_amount, alt_amount, btc_alt, symbol, btc_precision, alt_precision):
        """
            calculating amount to btc_amount from from_object
            calculating amount to alt_amount from to_object

            Args:
                btc_amount: BTC amount from from_object
                alt_amount: ALT amount from to_object
                btc_alt: symbol's bids
                btc_precision: precision of BTC
                alt_precision: precision of ALT
        """
        btc_amount = float(btc_amount)
        alt_btc = float(alt_amount) * float(btc_alt['bids'])

        if btc_amount < alt_btc:
            # from_object에 있는 BTC보다 to_object에서 alt를 판매할 때 나오는 btc의 수량이 더 높은경우
            alt_amount = Decimal(float(btc_amount) / float(btc_alt['bids'])).quantize(Decimal(10) ** alt_precision,
                                                                                      rounding=ROUND_DOWN)
            return btc_amount, alt_amount
        else:
            # from_object에 있는 BTC의 수량이 to_object에서 alt를 판매할 때 나오는 btc의 수량보다 더 높은경우
            alt_amount = Decimal(float(alt_amount)).quantize(Decimal(10) ** alt_precision, rounding=ROUND_DOWN)
            return alt_btc, alt_amount

    def manually_withdraw(self, from_object, to_object, max_profit, send_amount, alt):
        self.log.send(Msg.Trade.NO_ADDRESS.format(to_exchange=to_object.name, alt=alt))
        self.log.send(Msg.Trade.ALT_WITHDRAW.format(
            from_exchange=from_object.name,
            to_exchange=to_object.name,
            alt=alt,
            unit=float(send_amount)
        ))
        btc_send_amount = calculate_withdraw_amount(max_profit.tradable_btc, to_object.transaction_fee['BTC'])
        self.log.send(Msg.Trade.BTC_WITHDRAW.format(
            to_exchange=to_object.name,
            from_exchange=from_object.name,
            unit=float(btc_send_amount)
        ))

        self.stop()
        return True

    def _withdraw(self, sender_object, receiver_object, profit_object, send_amount, coin):
        """
            Function for sending profit
            Args:
                sender_object: It is a object to send the profit amount to receiver_object
                receiver_object: It is a object to receive the profit amount
                profit_object: information of profit

            sender_object: 이 거래소에서 coin 값을 send_amount만큼 보낸다.
            receiver_object: 이 거래소에서 coin 값을 send_amount만큼 받는다.
        """
        if self.auto_withdrawal:
            while not self.stop_flag:
                if check_deposit_addrs(coin, receiver_object.deposit):
                    if coin in TAG_COINS:
                        res_object = sender_object.exchange.withdraw(coin, send_amount, receiver_object.deposit[coin],
                                                                   receiver_object.deposit[coin + 'TAG'])
                    else:
                        res_object = sender_object.exchange.withdraw(coin, send_amount, receiver_object.deposit[coin])

                    if res_object.success:
                        return True
                    else:
                        self.log.send(Msg.Trade.FAIL_WITHDRAWAL.format(
                            from_exchange=sender_object.name,
                            to_exchange=receiver_object.name,
                            alt=coin
                        ))
                        self.log.send(Msg.Trade.ERROR_CONTENTS.format(error_string=res_object.message))
                        self.log.send(Msg.Trade.REQUEST_MANUAL_STOP)
                        time.sleep(res_object.time)
                        continue
                else:
                    self.manually_withdraw(sender_object, receiver_object, profit_object, send_amount, coin)
                    return
            else:
                self.manually_withdraw(sender_object, receiver_object, profit_object, send_amount, coin)
                return
        else:
            self.manually_withdraw(sender_object, receiver_object, profit_object, send_amount, coin)
            return

    def _trade(self, from_object, to_object, profit_object):
        """
            Function for trading coins
            from_object: A object that will be buying the ALT coin
            to_object: A object that will be selling the ALT coin
            profit_object: information of profit
        """

        alt = profit_object.currency.split('_')[1]

        res_object = from_object.exchange.base_to_alt(profit_object.currency, profit_object.tradable_btc,
                                                      profit_object.alt_amount, from_object.trading_fee,
                                                      to_object.trading_fee)

        if not res_object.success:
            raise

        from_object_alt_amount = res_object.data

        debugger.debug(Msg.Debug.BUY_ALT.format(from_exchange=from_object.name, alt=alt))

        self.secondary.alt_to_base(profit_object.currency, profit_object.tradable_btc, from_object_alt_amount)
        debugger.debug(Msg.Debug.SELL_ALT.format(to_exchange=to_object.name, alt=alt))
        debugger.debug(Msg.Debug.BUY_BTC.format(to_exchange=to_object.name))

        # from_object -> to_object 로 ALT 보냄
        send_amount = calculate_withdraw_amount(from_object_alt_amount, from_object.transaction_fee[alt])
        self._withdraw(from_object, to_object, profit_object, send_amount, alt)

        # to_object -> from_object 로 BTC 보냄
        btc_send_amount = calculate_withdraw_amount(profit_object.tradable_btc, to_object.transaction_fee['BTC'])
        self._withdraw(to_object, from_object, profit_object, btc_send_amount, 'BTC')

    def trade(self, profit_object):
        self.log.send(Msg.Trade.START_TRADE)
        if self.auto_withdrawal:
            if not self.primary_obj.deposit or not self.secondary_obj.deposit:
                # 입금 주소 없음
                return False

        if profit_object.trade == PRIMARY_TO_SECONDARY:
            self._trade(self.primary_obj, self.secondary_obj, profit_object)
        else:
            self._trade(self.secondary_obj, self.primary_obj, profit_object)

        return True

# Python Inner parties
import time
import random
import asyncio

from decimal import Decimal, ROUND_DOWN
from datetime import datetime

# SAI parties
from Bithumb.bithumb import Bithumb
from Binance.binance import Binance
from Bitfinex.bitfinex import Bitfinex
from Upbit.upbit import BaseUpbit
from Huobi.huobi import Huobi

from pyinstaller_patch import *
# END

# Domain parties
from settings.messages import Logs
from settings.messages import Messages as Msg
from settings.defaults import TAG_COINS, PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY
from trade_utils import send_amount_calculator, expect_profit_sender, \
    is_exists_deposit_addrs


# Third parties
import requests
from PyQt5.QtCore import pyqtSignal, QThread


# temp
EXCHANGES = ['bithumb', 'binance']
EXCLUDE_EXCHANGES = ['korbit']
TEST_COINS = [
    'BTC', 'ETH', 'BCC', 'XRP', 'ETC', 'QTUM', 'XMR', 'ZEC'
]

RANDOMLY_INT = (10, 100)



"""
    모든 함수 값에 self가 있으면, self를 우선순위로 둬야함
    def send(primary, secondary)
        --> 이 경우 이미 self.primary_obj.exchange가 있으므로 
    
    def send():
        self.primary_obj.exchange ... 로 처리
"""


class MaxProfits(object):
    def __init__(self, btc_profit, tradable_btc, alt_amount, currency, trade):
        self.btc_profit = btc_profit
        self.tradable_btc = tradable_btc
        self.alt_amount = alt_amount,
        self.currency = currency
        self.trade_type = trade

        self.information = None


class ExchangeInfo(object):
    # todo primary_info는 diff_trader에 받고있는데, 하나의 DICT에 하나의 거래소만 받는데 왜 dict처리하는지 확인 필요함.
    #  이유가 없으면 삭제하기
    def __init__(self, cfg, name, log):
        # todo property, setter의 사용성에 대해 재고가 필요, 만약에 변수들에 대한 처리가 많아야 하는 경우에는 필요할듯.
        self._log = log
        self.__cfg = cfg
        self.__name = None
        if EXCHANGES in name:
            self.__name = name

        self.__exchange = None

        if 'pydevd' in sys.modules:
            self.__balance = {x: random.randint(*RANDOMLY_INT) for x in TEST_COINS}
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
        if EXCHANGES in val:
            # name값이 정상인 경우에만 insert
            self.__name = val

    @property
    def exchange(self):
        return self.__exchange

    @exchange.setter
    def exchange(self, val):
        # todo 정상 여부 확인, 정상인 경우 insert
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
    """
        TradeThread
        That for calculate the profit between primary exchange and secondary exchange, trading, withdrawal, etc
        TradeThread, 첫번째, 두번째 거래소의 차익 계산, 거래 등 전체적인 트레이딩 로직
    """
    log_signal = pyqtSignal(int, str)
    stopped = pyqtSignal()
    profit_signal = pyqtSignal(str, float)

    def __init__(self, email, primary_info, secondary_info, min_profit_per, min_profit_btc, auto_withdrawal):
        super().__init__()
        self.stop_flag = True
        self.log = Logs(self.log_signal)
        self.email = email
        self.min_profit_per = min_profit_per
        self.min_profit_btc = min_profit_btc
        self.auto_withdrawal = auto_withdrawal

        self.primary_obj = ExchangeInfo(cfg=primary_info, name=list(primary_info.keys())[0], log=self.log)
        self.secondary_obj = ExchangeInfo(cfg=secondary_info, name=list(secondary_info.keys())[0], log=self.log)
        # todo 없애고 exchange_info로 통합할지 생각.
        self.primary_exchange_str = self.exchange_info['primary']['name']
        self.secondary_exchange_str = self.exchange_info['secondary']['name']

        self.collected_data = dict()
        self.currencies = None

    def stop(self):
        self.stop_flag = True

    def run(self):
        for info in [self.primary_obj, self.secondary_obj]:
            info.exchange = self.get_exchange(info.name, info.cfg)

        if not self.primary_obj.exchange or not self.secondary_obj.exchange:
            self.stop()
            self.stopped.emit()
            return

        self.stop_flag = False
        try:
            # todo 이 부분에 대해서 별도 object로 검증을 미리 해놓을지 학인 필요함.
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
                        tx_res = await self.get_tx_fees()
                        td_res = await self.get_td_fees()

                        if not (tx_res and td_res):
                            # need fail logs
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

                    # todo orderbook은 뭘 리턴받지? 확인필요함
                    success, data, error, time_ = await self.compare_orderbook(default_btc)
                    if not success:
                        self.log.send(Msg.Trade.ERROR_CONTENTS.format(error_string=error))
                        time.sleep(time_)
                        continue

                    # btc_profit, tradable_btc, alt_amount, currency, trade
                    profit_object = self.get_max_profit(data)
                    if not profit_object:
                        self.log.send(Msg.Trade.NO_PROFIT)
                        expect_profit_sender(profit_object)

                        continue
                    if profit_object.btc_profit >= self.min_profit_btc:
                        #   사용자 지정 BTC 보다 많은경우
                        try:
                            trade_success = self.trade(profit_object)

                            # profit 수집
                            expect_profit_sender(profit_object)

                            if not trade_success:
                                self.log.send(Msg.Trade.FAIL)
                                continue
                            self.log.send(Msg.Trade.SUCCESS)

                        except:
                            #   trade 함수 내에서 처리하지 못한 함수가 발견한 경우
                            debugger.exception(Msg.Error.EXCEPTION)
                            self.log.send_error(Msg.Error.EXCEPTION)
                            expect_profit_sender(profit_object)

                            return False
                    else:
                        #   사용자 지정 BTC 보다 적은경우
                        self.log.send(Msg.Trade.NO_MIN_BTC)
                        expect_profit_sender(profit_object)

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
            suc, data, msg, st = exchange.get_account_id()
            if not suc:
                self.log.send(msg)
                return False

            return exchange

    async def deposits(self):
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.get_deposit_addrs(), self.secondary_obj.exchange.get_deposit_addrs()
        )
        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            raise

        self.primary_obj.deposit = primary_res.data
        self.secondary_obj.deposit = secondary_res.data

        return True

    async def get_tx_fees(self):
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.get_trading_fee(),
            self.secondary_obj.exchange.get_trading_fee(),
        )

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            raise

        self.primary_obj.trading_fee = primary_res.data
        self.secondary_obj.trading_fee = secondary_res.data

    async def get_td_fees(self):
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.get_transaction_fee(),
            self.secondary_obj.exchange.get_transaction_fee()
        )

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            raise

        self.primary_obj.transaction_fee = primary_res.data
        self.secondary_obj.transaction_fee = secondary_res.data

    def get_precision(self, currency):
        primary_res = self.primary_obj.exchange.get_precision(currency)
        secondary_res = self.secondary_obj.exchange.get_precision(currency)

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            return False

        primary_btc_precision, primary_alt_precision = primary_res.data
        secondary_btc_precision, secondary_alt_precision = secondary_res.data

        btc_precision = max(primary_btc_precision, secondary_btc_precision)
        alt_precision = max(secondary_btc_precision, secondary_alt_precision)

        return btc_precision, alt_precision

    async def balance_and_currencies(self):
        """
            balance 값은 모두 int, float의 값이어야 함 ( string값은 리턴받아선 안됨 )
        """
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.balance(),
            self.secondary_obj.exchange.balance()
        )

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            raise

        self.primary_obj.balance = primary_res.data
        self.secondary_obj.balance = secondary_res.data

        self.currencies = list(set(self.secondary_obj.balance).intersection(self.primary_obj.balance))

        return True

    async def compare_orderbook(self, default_btc=1.0):
        primary_res, secondary_res = await asyncio.gather(
            self.primary_obj.exchange.get_curr_avg_orderbook(self.currencies, default_btc),
            self.secondary_obj.exchange.get_curr_avg_orderbook(self.currencies, default_btc)
        )

        for res in [primary_res, secondary_res]:
            if not res.success:
                self.log.send(Msg.Trade.ERROR_CONTENTS.format(res.message))

        if not primary_res.success or not secondary_res.success:
            return False

        m_to_s = dict()
        for currency_pair in self.currencies:
            m_ask = primary_res.data[currency_pair]['asks']
            s_bid = secondary_res.data[currency_pair]['bids']
            m_to_s[currency_pair] = float(((s_bid - m_ask) / m_ask))

        s_to_m = dict()
        for currency_pair in self.currencies:
            m_bid = primary_res.data[currency_pair]['bids']
            s_ask = secondary_res.data[currency_pair]['asks']
            s_to_m[currency_pair] = float(((m_bid - s_ask) / s_ask))

        res = primary_res.data, secondary_res.data, {'m_to_s': m_to_s, 's_to_m': s_to_m}

        return res

    def get_expectation_by_balance(self, from_object, to_object, currency, alt, btc_precision, alt_precision, real_diff):
        """

        """
        tradable_btc, alt_amount = self.find_min_balance(from_object.balance['BTC'],
                                                         to_object.balance[alt],
                                                         to_object.orderbook[currency], currency,
                                                         btc_precision, alt_precision)

        tradable_btc = tradable_btc.quantize(Decimal(10) ** -4, rounding=ROUND_DOWN)

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
        profit_object = None
        primary_orderbook, secondary_orderbook, data = data
        for trade in [PRIMARY_TO_SECONDARY, SECONDARY_TO_PRIMARY]:
            if self.primary_exchange_str == 'korbit' and trade == PRIMARY_TO_SECONDARY:
                continue
            for currency in self.currencies:
                alt = currency.split('_')[1]
                if not self.primary_obj.balance.get(alt):
                    self.log.send(Msg.Trade.NO_BALANCE_ALT.format(exchange=self.primary_exchange_str, alt=alt))
                    continue
                elif not self.secondary_obj.balance.get(alt):
                    self.log.send(Msg.Trade.NO_BALANCE_ALT.format(exchange=self.secondary_exchange_str, alt=alt))
                    continue

                if trade == PRIMARY_TO_SECONDARY and data[trade][currency] >= 0:
                    from_, to, asks, bids, profit_per = self.primary_exchange_str, self.secondary_exchange_str, \
                                                        primary_orderbook[currency]['asks'], \
                                                        secondary_orderbook[currency]['bids'], \
                                                        data[trade][currency] * 100,
                else:  # trade == SECONDARY_TO_PRIMARY and data[trade][currency] >= 0:
                    from_, to, asks, bids, profit_per = self.secondary_exchange_str, self.primary_exchange_str, \
                                                        secondary_orderbook[currency]['asks'], \
                                                        primary_orderbook[currency]['bids'], \
                                                        data[trade][currency] * 100

                self.log.send(Msg.Trade.EXCEPT_PROFIT.format(
                    from_exchange=from_,
                    to_exchange=to,
                    currency=currency,
                    profit_per=profit_per
                ))
                debugger.debug(Msg.Debug.ASK_BID.format(
                    currency=currency,
                    from_exchange=from_,
                    from_asks=asks,
                    to_exchange=to,
                    to_bids=bids
                ))

                expect_profit_percent = data.get(trade, dict()).get(currency, int())

                if expect_profit_percent < self.min_profit_per:
                    continue

                # TODO unit:coin = Decimal, unit:percent = float
                # real_diff 부분은 원화마켓과 BTC마켓의 수수료가 부과되는 횟수가 달라서 거래소 별로 다르게 지정해줘야함
                # 내부에서 부과회수(함수로 만듬 fee_count)까지 리턴해서 받아오는걸로 처리한다.

                primary_trade_fee_percent = (1 - self.primary_obj.trading_fee) ** self.primary_obj.fee_cnt
                secondary_trade_fee_percent = (1 - self.secondary_obj.trading_fee) ** self.secondary_obj.fee_cnt

                real_diff = ((1 + data[trade][currency]) * primary_trade_fee_percent * secondary_trade_fee_percent) - 1

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
                        # alt_amount로 거래할 btc를 맞춰줌, BTC를 사고 ALT를 팔기때문에 bids가격을 곱해야함
                        # tradable_btc = alt_amount * data['s_o_b'][currency]['bids']
                    else:
                        tradable_btc, alt_amount, btc_profit = self.get_expectation_by_balance(
                            self.secondary_obj, self.primary_obj, currency, alt, btc_precision, alt_precision
                        )

                    debugger.debug(Msg.Debug.TRADABLE_BTC.format(tradable_btc=tradable_btc))
                    debugger.debug(Msg.Debug.TRADABLE_ASK_BID.format(
                        from_exchange=self.secondary_exchange_str,
                        from_orderbook=secondary_orderbook[currency],
                        to_exchange=self.primary_exchange_str,
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
        btc_amount = Decimal(float(btc_amount)).quantize(Decimal(10) ** btc_precision, rounding=ROUND_DOWN)
        alt_btc = Decimal(float(alt_amount) * float(btc_alt['bids'])).quantize(Decimal(10) ** -8,
                                                                               rounding=ROUND_DOWN)
        if btc_amount < alt_btc:
            alt_amount = Decimal(float(btc_amount) / float(btc_alt['bids'])).quantize(Decimal(10) ** alt_precision,
                                                                                      rounding=ROUND_DOWN)
            return btc_amount, alt_amount
        else:
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
        btc_send_amount = send_amount_calculator(max_profit.tradable_btc, to_object.transaction_fee['BTC'])
        self.log.send(Msg.Trade.BTC_WITHDRAW.format(
            to_exchange=to_object.name,
            from_exchange=from_object.name,
            unit=float(btc_send_amount)
        ))
    
        self.stop()
        return True

    def coin_trader(self, sender_object, receiver_object, profit_object, send_amount, coin):
        """
            sender_object: 이 거래소에서 coin 값을 send_amount만큼 보낸다.
            receiver_object: 이 거래소에서 coin 값을 send_amount만큼 받는다.
        """
        if self.auto_withdrawal:
            while not self.stop_flag:
                if is_exists_deposit_addrs(coin, receiver_object.deposit):
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

    def trade_controller(self, from_object, to_object, profit_object):
        """
            from_object: ALT를 사게되는 거래소
            to_object: ALT를 팔게되는 거래소
            profit_object: from_object에서 to_object에서 수익관련 object
        """

        alt = profit_object.currency.split('_')[1]
        
        res_object = from_object.exchange.base_to_alt(profit_object.currency, profit_object.tradable_btc,
                                                      profit_object.alt_amount, from_object.trading_fee,
                                                      to_object.trading_fee)
        
        from_object_alt_amount = res_object.data
        
        debugger.debug(Msg.Debug.BUY_ALT.format(from_exchange=from_object.name, alt=alt))

        self.secondary.alt_to_base(profit_object.currency, profit_object.tradable_btc, from_object_alt_amount)
        debugger.debug(Msg.Debug.SELL_ALT.format(to_exchange=to_object.name, alt=alt))
        debugger.debug(Msg.Debug.BUY_BTC.format(to_exchange=to_object.name))

        if not res_object.success:
            raise
        
        # from_object -> to_object 로 ALT 보냄
        send_amount = send_amount_calculator(from_object_alt_amount, from_object.transaction_fee[alt])
        self.coin_trader(from_object, to_object, profit_object, send_amount, alt)

        # to_object -> from_object 로 BTC 보냄
        btc_send_amount = send_amount_calculator(profit_object.tradable_btc, to_object.transaction_fee['BTC'])
        self.coin_trader(to_object, from_object, profit_object, btc_send_amount, 'BTC')

    def trade(self, profit_object):
        self.log.send(Msg.Trade.START_TRADE)
        if self.auto_withdrawal:
            if not self.primary_obj.deposit or not self.secondary_obj.deposit:
                # 입금 주소 없음
                False

        if profit_object.trade == PRIMARY_TO_SECONDARY:
            self.trade_controller(self.primary_obj, self.secondary_obj, profit_object)
        else:
            self.trade_controller(self.secondary_obj, self.primary_obj, profit_object)

        return True

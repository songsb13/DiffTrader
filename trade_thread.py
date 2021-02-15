from pyinstaller_patch import *
from PyQt5.QtCore import pyqtSignal, QThread
from decimal import Decimal, ROUND_DOWN
from datetime import datetime
import asyncio
from telegram import Bot

from Bithumb.bithumb import Bithumb
from Binance.binance import Binance
from Bitfinex.bitfinex import Bitfinex
from Upbit.upbit import UpbitBTC, UpbitUSDT, UpbitKRW
from Huobi.huobi import Huobi
from settings.messages import Logs
from settings.messages import Messages as Msg
import time
import random


# temp
EXCHANGES = ['bithumb', 'binance']
EXCLUDE_EXCHANGES = ['korbit']
TEST_COINS = [
    'BTC', 'ETH', 'BCC', 'XRP', 'ETC', 'QTUM', 'XMR', 'ZEC'
]

RANDOMLY_INT = (10, 100)

# primary에서 BTC매도(ALT매수) -> secondary에서 ALT매도(BTC로 변환)
PRIMARY_TO_SECONDARY = 'mts'

# secondary에서 BTC매도(ALT매수) -> primary에서 ALT매도(BTC로 변환)
SECONDARY_TO_PRIMARY = 'stm'



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
        self.__fee = None
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
    def fee(self):
        return self.__fee

    @fee.setter
    def fee(self, val):
        self.__fee = val
        
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
            else:
                deposit = None
            fee_refresh_time = int()
            while evt.is_set() and not self.stop_flag:
                try:
                    if time.time() >= fee_refresh_time + 600:
                        res = await self.fees()

                        if not res:
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
                        # balance 없는 경우
                        self.log.send(Msg.Trade.NO_BALANCE_BTC)
                        continue

                    # todo orderbook은 뭘 리턴받지? 확인필요함
                    success, data, error, time_ = await self.primary_obj.exchange.compare_orderbook(
                        self.secondary_obj.exchange, self.currencies, default_btc
                    )
                    if not success:
                        self.log.send(Msg.Trade.ERROR_CONTENTS.format(error_string=error))
                        time.sleep(time_)
                        continue

                    # btc_profit, tradable_btc, alt_amount, currency, trade
                    profit_object = self.get_max_profit(data)
                    if not profit_object:
                        self.log.send(Msg.Trade.NO_PROFIT)
                        self.save_profit_expected(data, self.currencies,
                                                  self.primary_exchange_str, self.secondary_exchange_str)
                        continue
                    if profit_object.btc_profit >= self.min_profit_btc:
                        #   사용자 지정 BTC 보다 많은경우
                        try:
                            success, res, msg, st = self.trade(max_profit, deposit, fee)

                            # profit 수집
                            sai_url = 'http://www.saiblockchain.com/api/pft_data'
                            try:
                                requests.post(sai_url, data=self.collected_data)
                                success = self.save_profit_expected(data, bal_n_crncy[2], self.primary_exchange_str,
                                                                    self.secondary_exchange_str)
                            except:
                                pass

                            if not success:
                                self.log.send(Msg.Trade.FAIL)
                                continue
                            self.log.send(Msg.Trade.SUCCESS)

                        except:
                            #   trade 함수 내에서 처리하지 못한 함수가 발견한 경우
                            debugger.exception(Msg.Error.EXCEPTION)
                            self.log.send_error(Msg.Error.EXCEPTION)
                            self.save_profit_expected(data, bal_n_crncy[2],
                                                      self.primary_exchange_str, self.secondary_exchange_str)
                            return False
                    else:
                        #   사용자 지정 BTC 보다 적은경우
                        self.log.send(Msg.Trade.NO_MIN_BTC)
                        self.save_profit_expected(data, bal_n_crncy[2],
                                                  self.primary_exchange_str, self.secondary_exchange_str)

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
            if exchange_str == 'UpbitBTC':
                exchange = UpbitBTC(cfg['id'], cfg['pw'], cfg['tkey'], cfg['tchatid'])
            elif exchange_str == 'UpbitUSDT':
                exchange = UpbitUSDT(cfg['id'], cfg['pw'], cfg['tkey'], cfg['tchatid'])
            elif exchange_str == 'UpbitKRW':
                exchange = UpbitKRW(cfg['id'], cfg['pw'], cfg['tkey'], cfg['tchatid'])
            else:
                return False
            try:
                exchange.bot = Bot(token=exchange.token)
            except:
                self.log_signal.emit(logging.INFO, "잘못된 텔레그램 봇 토큰입니다.")
                return False
            try:
                exchange.bot.get_chat(exchange.chat_id)
            except:
                self.log_signal.emit(logging.INFO,
                                     ("존재하지 않는 채팅 아이디 입니다.\n"
                                      "채팅 아이디가 올바르다면 봇에게 메세지를 보낸 후 다시 시도해 주세요."))
                return False

            self.log_signal.emit(logging.INFO, "[{}] 업비트 인증을 시작합니다.".format(exchange_str))
            if 'pydevd' in sys.modules:
                exchange.chrome(headless=False)
            else:
                exchange.chrome(headless=True)
            while True:
                success, tokens, msg, st = exchange.sign_in(cfg['id'], cfg['pw'])
                if not tokens:
                    self.log_signal.emit(logging.INFO, msg)
                    exchange.off()
                    if '비밀번호' in msg:
                        return False
                    time.sleep(st)
                    exchange.chrome(headless=True)
                else:
                    exchange.decrypt_token(tokens)
                    exchange.off()
                    break
            return exchange
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

    async def fees(self):
        fut = [
            self.primary_obj.exchange.get_trading_fee(),
            self.secondary_obj.exchange.get_trading_fee(),
            self.primary_obj.exchange.get_transaction_fee(),
            self.secondary_obj.exchange.get_transaction_fee()
        ]
        ret = await asyncio.gather(*fut)
        ts = 0
        err = False
        if not ret[0][0]:
            self.log.send(ret[0][2])
            ts = ret[0][3]
            err = True
        if not ret[1][0]:
            self.log.send(ret[1][2])
            if ts < ret[1][3]:
                ts = ret[1][3]
            err = True
        if not ret[2][0]:
            self.log.send(ret[2][2])
            if ts < ret[2][3]:
                ts = ret[2][3]
            err = True
        if not ret[3][0]:
            self.log.send(ret[3][2])
            if ts < ret[3][3]:
                ts = ret[3][3]
            err = True
        if err:
            time.sleep(ts)
            return False
        else:
            return ret[0][1], ret[1][1], ret[2][1], ret[3][1]

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

    def get_expectation_by_balance(self, from_object, to_object, currency, alt, btc_precision, alt_precision):
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
                Decimal(primary_tx_fee[alt]) * primary_orderbook[currency]['asks']) - Decimal(
            secondary_tx_fee['BTC'])

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

                primary_trade_fee_percent = (1 - self.primary_obj.fee) ** self.primary_obj.fee_cnt
                secondary_trade_fee_percent = (1 - self.secondary_obj.fee) ** self.secondary_obj.fee_cnt

                real_diff = ((1 + data[trade][currency]) * primary_trade_fee_percent * secondary_trade_fee_percent) - 1

                # get precision of BTC and ALT
                precision_set = self.get_precision(currency)
                if not precision_set:
                    return False
                btc_precision, alt_precision = precision_set

                try:
                    if trade == PRIMARY_TO_SECONDARY:
                        tradable_btc, alt_amount, btc_profit = self.get_expectation_by_balance(
                            self.primary_obj, self.secondary_obj, currency, alt, btc_precision, alt_precision
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
                    primary_market=self.primary_exchange_str,
                    secondary_market=self.secondary_exchange_str,
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

    def save_profit_expected(self, profits, currencies, primary_name: str, secondary_name: str):
        """
        :param profits: 예상차익
        :param currencies: 거래될 코인종류
        :param primary_name: 주 거래소 이름
        :param secondary_name: 보조 거래소 이름
        :return: Boolean
        """
        #   m_to_s, s_to_m 정보가 담긴 딕셔너리만 보낸다. 0: primary orderbook, 1: secondary orderbook
        profit = profits[2]
        try:
            r = requests.get("http://saiblockchain.com/api/expected_profit",
                             json={'profit': profit, 'currencies': currencies, 'primary': primary_name,
                                   'secondary': secondary_name})
            if r.status_code == 200:
                return True
            else:
                return False
        except:
            debugger.exception(Msg.Error.FATAL)
            return False

    def trade(self, max_profit, deposit_addrs, fee):
        """
        :param max_profit:
        :param deposit_addrs:
        :param fee:
        :return:
        """
        
        self.log.send(Msg.Trade.START_TRADE)
        btc_profit, tradable_btc, alt_amount, currency, trade = max_profit
        primary_trade_fee, secondary_trade_fee, primary_tx_fee, secondary_tx_fee = fee
        if self.auto_withdrawal:
            primary_deposit_addrs, secondary_deposit_addrs = deposit_addrs
            if not primary_deposit_addrs or not secondary_deposit_addrs:
                return False, '', '메인 또는 서브 거래소 입금주소가 존재하지 않습니다', 0

        alt = currency.split('_')[1]

        if trade == 'm_to_s':
            #   거래소1 에서 ALT 를 사고(btc를팔고) 거래소2 에서 BTC 를 사서(ALT를팔고) 교환함
            suc, res, msg, st = self.primary.base_to_alt(currency, tradable_btc, alt_amount, primary_trade_fee,
                                                         primary_tx_fee)  # ,'buy')
            if not suc:
                return False, '', msg, st
            
            debugger.debug(Msg.Debug.BUY_ALT.format(from_exchange=self.primary_exchange_str, alt=alt))
            alt_amount = res

            # 무조건 성공해야하는 부분이기때문에 return값이 없다
            self.secondary.alt_to_base(currency, tradable_btc, alt_amount)
            debugger.debug(Msg.Debug.SELL_ALT.format(to_exchange=self.secondary_exchange_str, alt=alt))
            debugger.debug(Msg.Debug.BUY_BTC.format(to_exchange=self.secondary_exchange_str))
            
            send_amount = alt_amount + Decimal(primary_tx_fee[alt]).quantize(
                Decimal(10) ** alt_amount.as_tuple().exponent)

            if self.primary_exchange_str.startswith("Upbit") and self.secondary_exchange_str.startswith("Upbit"):
                return True, '', '', 0

            if self.auto_withdrawal:
                while not self.stop_flag:
                    #   거래소1 -> 거래소2 ALT 이체
                    if alt == 'XRP' or alt == 'XMR':
                        if (alt not in secondary_deposit_addrs
                                or alt + 'TAG' not in secondary_deposit_addrs
                                or not secondary_deposit_addrs[alt]
                                or not secondary_deposit_addrs[alt + 'TAG']):
                            
                            self.log.send(Msg.Trade.NO_ADDRESS.format(to_exchange=self.secondary_exchange_str, alt=alt))
                            self.log.send(Msg.Trade.ALT_WITHDRAW.format(
                                from_exchange=self.primary_exchange_str,
                                to_exchange=self.secondary_exchange_str,
                                alt=alt,
                                unit=float(send_amount)
                            ))
                            send_amount = tradable_btc + Decimal(secondary_tx_fee['BTC']).quantize(
                                Decimal(10) ** tradable_btc.as_tuple().exponent)
                            
                            self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                                to_exchange=self.secondary_exchange_str,
                                from_exchange=self.primary_exchange_str,
                                unit=float(send_amount)
                            ))
                            
                            self.stop()
                            return True, '', '', 0
                        res = self.primary.withdraw(alt, float(send_amount), secondary_deposit_addrs[alt],
                                                    secondary_deposit_addrs[alt + 'TAG'])
                    else:
                        if alt not in secondary_deposit_addrs or not secondary_deposit_addrs[alt]:
                            self.log.send(Msg.Trade.NO_ADDRESS.format(to_exchange=self.secondary_exchange_str, alt=alt))
                            self.log.send(Msg.Trade.ALT_WITHDRAW.format(
                                from_exchange=self.primary_exchange_str,
                                to_exchange=self.secondary_exchange_str,
                                alt=alt,
                                unit=float(send_amount)
                            ))
                            send_amount = tradable_btc + Decimal(secondary_tx_fee['BTC']).quantize(
                                Decimal(10) ** tradable_btc.as_tuple().exponent)
                            self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                                to_exchange=self.secondary_exchange_str,
                                from_exchange=self.primary_exchange_str,
                                unit=float(send_amount)
                            ))
                            self.stop()
                            return True, '', '', 0
                        res = self.primary.withdraw(alt, send_amount, secondary_deposit_addrs[alt])
                    if not res[0]:  # success 여부
                        self.log.send(Msg.Trade.FAIL_WITHDRAWAL.format(
                            from_exchange=self.primary_exchange_str,
                            to_exchange=self.secondary_exchange_str,
                            alt=alt
                        ))
                        self.log.send(Msg.Trade.ERROR_CONTENTS.format(error_string=res[2]))
                        self.log.send(Msg.Trade.REQUEST_MANUAL_STOP)
                        time.sleep(res[3])
                    else:
                        break
                else:
                    self.log.send(Msg.Trade.MANUAL_STOP)
                    self.log.send(Msg.Trade.ALT_WITHDRAW.format(
                        from_exchange=self.primary_exchange_str,
                        to_exchange=self.secondary_exchange_str,
                        alt=alt,
                        unit=float(send_amount)
                    ))
                    send_amount = tradable_btc + Decimal(secondary_tx_fee['BTC']).quantize(
                        Decimal(10) ** tradable_btc.as_tuple().exponent)
                    self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                        to_exchange=self.secondary_exchange_str,
                        from_exchange=self.primary_exchange_str,
                        unit=float(send_amount)
                    ))
                    return True, '', '', 0

                self.log.send(Msg.Trade.ALT_WITHDRAW.format(
                    from_exchange=self.primary_exchange_str,
                    to_exchange=self.secondary_exchange_str,
                    alt=alt,
                    unit=float(send_amount)
                ))
                send_amount = tradable_btc + Decimal(secondary_tx_fee['BTC']).quantize(
                    Decimal(10) ** tradable_btc.as_tuple().exponent)
                while not self.stop_flag:
                    #   거래소2 -> 거래소1 BTC 이체
                    if 'BTC' not in primary_deposit_addrs or not primary_deposit_addrs['BTC']:
                        self.log.send(Msg.Trade.NO_BTC_ADDRESS.format(from_exchange=self.primary_exchange_str))
                        self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                            to_exchange=self.secondary_exchange_str,
                            from_exchange=self.primary_exchange_str,
                            unit=float(send_amount)
                        ))
                        self.stop()
                        return True, '', '', 0
                    res = self.secondary.withdraw('BTC', send_amount, primary_deposit_addrs['BTC'])
                    if res[0]:
                        break
                    else:
                        self.log.send(Msg.Trade.FAIL_BTC_WITHDRAWAL.format(
                            to_exchange=self.secondary_exchange_str,
                            from_exchange=self.primary_exchange_str
                        ))
                        self.log.send(Msg.Trade.ERROR_CONTENTS.format(error_string=res[2]))
                        self.log.send(Msg.Trade.REQUEST_MANUAL_STOP)
                        
                        time.sleep(res[3])
                else:
                    self.log.send(Msg.Trade.MANUAL_STOP)
                    self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                        to_exchange=self.secondary_exchange_str,
                        from_exchange=self.primary_exchange_str,
                        unit=float(send_amount)
                    ))
                    return True, '', '', 0

                self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                    to_exchange=self.secondary_exchange_str,
                    from_exchange=self.primary_exchange_str,
                    unit=float(send_amount)
                ))
            else:
                self.log.send(Msg.Trade.COMPLETE_MANUAL)
                self.stop()
        else:
            #   거래소1 에서 BTC 를 사고 거래소2 에서 ALT 를 사서 교환함
            suc, res, msg, st = self.secondary.base_to_alt(currency, tradable_btc, alt_amount, secondary_trade_fee,
                                                           secondary_tx_fee)
            if not suc:
                return False, '', msg, st
            
            debugger.debug(Msg.Debug.BUY_ALT.format(from_exchange=self.secondary_exchange_str, alt=alt))
            
            alt_amount = res
            self.primary.alt_to_base(currency, tradable_btc, alt_amount)
            
            debugger.debug(Msg.Debug.SELL_ALT.format(to_exchange=self.primary_exchange_str, alt=alt))
            debugger.debug(Msg.Debug.BUY_BTC.format(to_exchange=self.primary_exchange_str))
            send_amount = alt_amount + Decimal(secondary_tx_fee[alt]).quantize(
                Decimal(10) ** alt_amount.as_tuple().exponent)

            if self.primary_exchange_str.startswith("Upbit") and self.secondary_exchange_str.startswith("Upbit"):
                return True, '', '', 0

            if self.auto_withdrawal:
                while not self.stop_flag:
                    #   Bithumb -> Binance ALT 이체
                    if alt == 'XRP' or alt == 'XMR':
                        if (alt not in primary_deposit_addrs
                                or alt + 'TAG' not in primary_deposit_addrs
                                or not primary_deposit_addrs[alt]
                                or not primary_deposit_addrs[alt + 'TAG']):
                            self.log.send(Msg.Trade.NO_ADDRESS.format(to_exchange=self.primary_exchange_str, alt=alt))
                            self.log.send(Msg.Trade.ALT_WITHDRAW.format(
                                from_exchange=self.secondary_exchange_str,
                                to_exchange=self.primary_exchange_str,
                                alt=alt,
                                unit=float(send_amount)
                            ))
                            send_amount = tradable_btc + Decimal(primary_tx_fee['BTC']).quantize(
                                Decimal(10) ** tradable_btc.as_tuple().exponent)
                            self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                                to_exchange=self.primary_exchange_str,
                                from_exchange=self.secondary_exchange_str,
                                unit=float(send_amount)
                            ))
                            self.stop()
                            return True, '', '', 0
                        res = self.secondary.withdraw(alt, send_amount, primary_deposit_addrs[alt],
                                                      primary_deposit_addrs[alt + 'TAG'])
                    else:
                        if alt not in primary_deposit_addrs or not primary_deposit_addrs[alt]:
                            self.log.send(Msg.Trade.NO_ADDRESS.format(to_exchange=self.primary_exchange_str, alt=alt))
                            self.log.send(Msg.Trade.ALT_WITHDRAW.format(
                                from_exchange=self.secondary_exchange_str,
                                to_exchange=self.primary_exchange_str,
                                alt=alt,
                                unit=float(send_amount)
                            ))
                            send_amount = tradable_btc + Decimal(primary_tx_fee['BTC']).quantize(
                                Decimal(10) ** tradable_btc.as_tuple().exponent)
                            self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                                to_exchange=self.primary_exchange_str,
                                from_exchange=self.secondary_exchange_str,
                                unit=float(send_amount)
                            ))
                            self.stop()
                            return True, '', '', 0
                        res = self.secondary.withdraw(alt, send_amount, primary_deposit_addrs[alt])
                    if res[0]:
                        break
                    else:
                        self.log.send(Msg.Trade.FAIL_WITHDRAWAL.format(
                            from_exchange=self.secondary_exchange_str,
                            to_exchange=self.primary_exchange_str,
                            alt=alt
                        ))
                        self.log.send(Msg.Trade.ERROR_CONTENTS.format(error_string=res[2]))
                        self.log.send(Msg.Trade.REQUEST_MANUAL_STOP)
                        time.sleep(res[3])
                else:
                    self.log.send(Msg.Trade.MANUAL_STOP)
                    self.log.send(Msg.Trade.ALT_WITHDRAW.format(
                        from_exchange=self.secondary_exchange_str,
                        to_exchange=self.primary_exchange_str,
                        alt=alt,
                        unit=float(send_amount)
                    ))
                    send_amount = tradable_btc + Decimal(primary_tx_fee['BTC']).quantize(
                        Decimal(10) ** tradable_btc.as_tuple().exponent)
                    self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                        to_exchange=self.primary_exchange_str,
                        from_exchange=self.secondary_exchange_str,
                        unit=float(send_amount)
                    ))
                    return True, '', '', 0

                self.log.send(Msg.Trade.ALT_WITHDRAW.format(
                    from_exchange=self.secondary_exchange_str,
                    to_exchange=self.primary_exchange_str,
                    alt=alt,
                    unit=float(send_amount)
                ))
                send_amount = tradable_btc + Decimal(primary_tx_fee['BTC']).quantize(
                    Decimal(10) ** tradable_btc.as_tuple().exponent)
                while not self.stop_flag:
                    #   Binance -> Bithumb BTC 이체
                    if 'BTC' not in secondary_deposit_addrs or not secondary_deposit_addrs['BTC']:
                        self.log.send(Msg.Trade.NO_BTC_ADDRESS.format(from_exchange=self.secondary_exchange_str))
                        self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                            to_exchange=self.primary_exchange_str,
                            from_exchange=self.secondary_exchange_str,
                            unit=float(send_amount)
                        ))
                        self.stop()
                        return True, '', '', 0
                    res = self.primary.withdraw('BTC', send_amount, secondary_deposit_addrs['BTC'])
                    if not res[0]:
                        self.log.send(Msg.Trade.FAIL_BTC_WITHDRAWAL.format(
                            to_exchange=self.primary_exchange_str,
                            from_exchange=self.secondary_exchange_str
                        ))
                        self.log.send(Msg.Trade.ERROR_CONTENTS.format(error_string=res[2]))
                        self.log.send(Msg.Trade.REQUEST_MANUAL_STOP)
                        time.sleep(res[3])
                    else:
                        break
                else:
                    self.log.send(Msg.Trade.MANUAL_STOP)
                    self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                        to_exchange=self.primary_exchange_str,
                        from_exchange=self.secondary_exchange_str,
                        unit=float(send_amount)
                    ))
                    return True, '', '', 0

                self.log.send(Msg.Trade.BTC_WITHDRAW.format(
                    to_exchange=self.primary_exchange_str,
                    from_exchange=self.secondary_exchange_str,
                    unit=float(send_amount)
                ))
            else:
                self.log.send(Msg.Trade.COMPLETE_MANUAL)
                self.stop()

        return True, '', '', 0

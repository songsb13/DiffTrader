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


# temp
EXCHANGES = ['bithumb', 'binance']

"""
    모든 함수 값에 self가 있으면, self를 우선순위로 둬야함
    def send(primary, secondary)
        --> 이 경우 이미 self.primary_obj.exchange가 있으므로 
    
    def send():
        self.primary_obj.exchange ... 로 처리
"""


class ExchangeInfo(object):

    # todo primary_info는 diff_trader에 받고있는데, 하나의 DICT에 하나의 거래소만 받는데 왜 dict처리하는지 확인 필요함.
    #  이유가 없으면 삭제하기
    def __init__(self, cfg, name, log_signal):
        # todo property, setter의 사용성에 대해 재고가 필요, 만약에 변수들에 대한 처리가 많아야 하는 경우에는 필요할듯.
        self._log_signal = log_signal
        self.__cfg = cfg
        self.__name = None
        if EXCHANGES in name:
            self.__name = name

        self.__exchange = None

        self.__balance = None
        self.__fee = None
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
    def fee(self):
        return self.__fee

    @fee.setter
    def fee(self, val):
        self.__fee = val

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

        self.primary_obj = ExchangeInfo(cfg=primary_info, name=list(primary_info.keys())[0])
        self.secondary_obj = ExchangeInfo(cfg=secondary_info, name=list(secondary_info.keys())[0])
        # todo 없애고 exchange_info로 통합할지 생각.
        self.primary_exchange_str = self.exchange_info['primary']['name']
        self.secondary_exchange_str = self.exchange_info['secondary']['name']

        self.collected_data = dict()

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
                deposit = await self.deposits()
                if not deposit:
                    self.log.send(Msg.Init.FAIL_WITHDRAWAL_INFO)
                    return False
                self.log.send(Msg.Init.SUCCESS_WITHDRAWAL_INFO)
            else:
                deposit = None
            t = 0
            fee = []
            fee_cnt = (self.primary.fee_count(), self.secondary.fee_count())

            while evt.is_set() and not self.stop_flag:
                try:
                    if time.time() >= t + 600:
                        fee = await self.fees()
                        if not fee:
                            #   실패 했을 경우 다시 요청
                            continue
                        self.log.send(Msg.Trade.SUCCESS_FEE_INFO)
                        t = time.time()
                    bal_n_crncy = await self.balance_and_currencies(self.primary, self.secondary, deposit)
                    if not bal_n_crncy:
                        continue
                    if not bal_n_crncy[2]:
                        # Intersection 결과가 비어있는 경우
                        self.log.send(Msg.Trade.NO_AVAILABLE)
                        continue
                    try:
                        if bal_n_crncy[0]['BTC'] > bal_n_crncy[1]['BTC']:
                            default_btc = bal_n_crncy[0]['BTC'] * 1.5
                        else:
                            default_btc = bal_n_crncy[1]['BTC'] * 1.5
                    except:
                        self.log.send(Msg.Trade.NO_BALANCE_BTC)
                        continue
                    success, data, err, ts = await self.primary.compare_orderbook(
                        self.secondary, bal_n_crncy[2], default_btc
                    )
                    if not success:
                        self.log.send(Msg.Trade.ERROR_CONTENTS.format(error_string=err))
                        time.sleep(ts)
                        continue

                    # btc_profit, tradable_btc, alt_amount, currency, trade
                    max_profit = self.get_max_profit(data, bal_n_crncy, fee, fee_cnt)
                    if max_profit is None:
                        self.log.send(Msg.Trade.NO_PROFIT)
                        self.save_profit_expected(data, bal_n_crncy[2],
                                                  self.primary_exchange_str, self.secondary_exchange_str)
                        continue
                    if max_profit is False:
                        # 예상차익이 실수가 아닌경우
                        continue
                    btc_profit = max_profit[0]

                    if 'pydevd' in sys.modules:
                        # todo 차후 리팩토링에서 삭제 예정
                        try:
                            bot = Bot(token='607408701:AAGYRRnzUKTWRIdJvYzl8AQMlGz52vinoUA')
                            bot.get_chat('348748653')
                            bot.sendMessage('348748653',
                                            '[{}] {} - {}: {}'.format(bal_n_crncy[2], self.primary_exchange_str,
                                                                      self.secondary_exchange_str, data))
                        except:
                            self.log_signal.emit(logging.INFO, "텔레그램 메세지 전송 실패")

                    if btc_profit >= self.min_profit_btc:
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

    def get_precision(self, primary, secondary, currency):
        primary_ret = primary.get_precision(currency)
        secondary_ret = secondary.get_precision(currency)

        if not primary_ret[0]:
            self.log.send(primary_ret[2])
            time.sleep(primary_ret[3])
            return False
        elif not secondary_ret[0]:
            self.log.send(secondary_ret[2])
            time.sleep(secondary_ret[3])
            return False

        btc_precision = primary_ret[1][0] if primary_ret[1][0] >= secondary_ret[1][0] else secondary_ret[1][0]
        alt_precision = primary_ret[1][1] if primary_ret[1][1] >= secondary_ret[1][1] else secondary_ret[1][1]

        return btc_precision, alt_precision

    async def balance_and_currencies(self):
        result = await asyncio.gather(primary.balance(), secondary.balance())

        if False and 'pydevd' in sys.modules:
            primary_balance = {'BTC': 0.4, 'ETH': 10, 'BCC': 7, 'LTC': 55, 'XRP': 10000,
                               'ETC': 262, 'OMG': 1000, 'DASH': 1.5, 'XMR': 37, 'ADA': 55000,
                               'QTUM': 500, 'ZEC': 19, 'EOS': 1000, 'BTG': 200}
            secondary_balance = {'BTC': 0.4, 'ETH': 10, 'BCH': 7, 'LTC': 55, 'XRP': 10000,
                                 'ETC': 262, 'OMG': 1000, 'DASH': 1.5, 'XMR': 37,
                                 'QTUM': 500, 'ZEC': 19, 'BTG': 200}
        else:
            primary_balance, secondary_balance = result
            ts = 0
            err = False
            if not primary_balance[0]:
                self.log.send(primary_balance[2])
                ts = primary_balance[3]
                err = True
            else:
                primary_balance = primary_balance[1]
            if not secondary_balance[0]:
                self.log.send(secondary_balance[2])
                if ts < secondary_balance[3]:
                    ts = secondary_balance[3]
                err = True
            else:
                secondary_balance = secondary_balance[1]

            if err:
                time.sleep(ts)
                return False

        if self.primary_balance != primary_balance or self.secondary_balance != secondary_balance:
            self.primary_balance = primary_balance
            self.secondary_balance = secondary_balance
            self.log.send(Msg.Balance.CURRENT.format(exchange=self.primary_exchange_str, balance=primary_balance))
            self.log.send(Msg.Balance.CURRENT.format(exchange=self.secondary_exchange_str, balance=secondary_balance))
        currencies = list(set(secondary_balance).intersection(primary_balance))
        
        debugger.debug(Msg.Debug.TRADABLE.format(currencies))
        temp = []
        for c in currencies:  # Currency_pair의 필요성(BTC_xxx)
            if c == 'BTC':
                continue
            temp.append('BTC_' + c)
        return [primary_balance, secondary_balance, temp]

    def get_max_profit(self, data, balance, fee, fee_cnt):
        primary_balance, secondary_balance, currencies = balance
        primary_trade_fee, secondary_trade_fee, primary_tx_fee, secondary_tx_fee = fee
        primary_fee_cnt, secondary_fee_cnt = fee_cnt
        max_profit = None
        primary_orderbook, secondary_orderbook, data = data
        for trade in ['m_to_s', 's_to_m']:
            if self.primary_exchange_str == 'Korbit' and trade == 'm_to_s':
                # 코빗은 s_to_m만 가능
                continue
            for currency in currencies:
                alt = currency.split('_')[1]
                if alt not in primary_balance.keys() or not primary_balance[alt]:
                    self.log.send(Msg.Trade.NO_BALANCE_ALT.format(exchange=self.primary_exchange_str, alt=alt))
                    continue
                if alt not in secondary_balance.keys() or not secondary_balance[alt]:
                    self.log.send(Msg.Trade.NO_BALANCE_ALT.format(exchange=self.secondary_exchange_str, alt=alt))
                    continue

                if trade == 'm_to_s' and data[trade][currency] >= 0:
                    self.log.send(Msg.Trade.EXCEPT_PROFIT.format(
                        from_exchange=self.primary_exchange_str,
                        to_exchange=self.secondary_exchange_str,
                        currency=currency,
                        profit_per=data[trade][currency] * 100
                    ))
                    debugger.debug(Msg.Debug.ASK_BID.format(
                        currency=currency,
                        from_exchange=self.primary_exchange_str,
                        from_asks=primary_orderbook[currency]['asks'],
                        to_exchange=self.secondary_exchange_str,
                        to_bids=secondary_orderbook[currency]['bids']
                    ))
                elif data[trade][currency] >= 0:
                    self.log.send(Msg.Trade.EXCEPT_PROFIT.format(
                        from_exchange=self.secondary_exchange_str,
                        to_exchange=self.primary_exchange_str,
                        currency=currency,
                        profit_per=data[trade][currency] * 100
                    ))
                    debugger.debug(Msg.Debug.ASK_BID.format(
                            currency=currency,
                            from_exchange=self.secondary_exchange_str,
                            from_asks=primary_orderbook[currency]['asks'],
                            to_exchange=self.primary_exchange_str,
                            to_bids=secondary_orderbook[currency]['bids']
                    ))
                try:
                    if data[trade][currency] < self.min_profit_per:
                        #   예상 차익이 %를 넘지 못하는 경우
                        continue
                except ValueError:
                    #   float() 이 에러가 난 경우
                    self.log.send(Msg.Trade.MIN_PROFIT_ERROR)
                    return False
                # TODO unit:coin = Decimal, unit:percent = float
                # real_diff 부분은 원화마켓과 BTC마켓의 수수료가 부과되는 횟수가 달라서 거래소 별로 다르게 지정해줘야함
                # 내부에서 부과회수(함수로 만듬 fee_count)까지 리턴해서 받아오는걸로 처리한다.
                real_diff = ((1 + data[trade][currency]) * ((1 - primary_trade_fee) ** primary_fee_cnt) * (
                        (1 - secondary_trade_fee) ** secondary_fee_cnt)) - 1

                # get precision of BTC and ALT
                ret = self.get_precision(self.primary, self.secondary, currency)
                if not ret:
                    return False
                btc_precision, alt_precision = ret

                try:
                    if trade == 'm_to_s':
                        tradable_btc, alt_amount = self.find_min_balance(primary_balance['BTC'],
                                                                         secondary_balance[alt],
                                                                         secondary_orderbook[currency], currency,
                                                                         btc_precision, alt_precision)
                        self.log.send(Msg.Trade.TRADABLE.format(
                            from_exchange=self.primary_exchange_str,
                            to_exchange=self.secondary_exchange_str,
                            alt=alt,
                            alt_amount=alt_amount,
                            tradable_btc=tradable_btc
                        ))
                        btc_profit = (tradable_btc * Decimal(real_diff)) - (
                                Decimal(primary_tx_fee[alt]) * primary_orderbook[currency]['asks']) - Decimal(
                            secondary_tx_fee['BTC'])
                        
                        self.log.send(Msg.Trade.BTC_PROFIT.format(
                            from_exchange=self.primary_exchange_str,
                            to_exchange=self.secondary_exchange_str,
                            alt=alt,
                            btc_profit=btc_profit,
                            btc_profit_per=real_diff * 100
                        ))
                        
                        # alt_amount로 거래할 btc를 맞춰줌, BTC를 사고 ALT를 팔기때문에 bids가격을 곱해야함
                        # tradable_btc = alt_amount * data['s_o_b'][currency]['bids']
                    else:
                        tradable_btc, alt_amount = self.find_min_balance(
                            secondary_balance['BTC'], primary_balance[alt], primary_orderbook[currency], currency,
                            btc_precision, alt_precision
                        )
                        self.log.send(Msg.Trade.TRADABLE.format(
                            from_exchange=self.secondary_exchange_str,
                            to_exchange=self.primary_exchange_str,
                            alt=alt,
                            alt_amount=alt_amount,
                            tradable_btc=tradable_btc
                        ))
                        
                        btc_profit = (tradable_btc * Decimal(real_diff)) - (
                                Decimal(secondary_tx_fee[alt]) * secondary_orderbook[currency]['asks']) - Decimal(
                            primary_tx_fee['BTC'])
                        
                        self.log.send(Msg.Trade.BTC_PROFIT.format(
                            from_exchange=self.secondary_exchange_str,
                            to_exchange=self.primary_exchange_str,
                            alt=alt,
                            btc_profit=btc_profit,
                            btc_profit_per=real_diff * 100
                        ))

                        # alt_amount로 거래할 btc를 맞춰줌, ALT를 사고 BTC를 팔기때문에 asks가격을 곱해야함
                        # tradable_btc = alt_amount * data['s_o_b'][currency]['asks']

                    tradable_btc = tradable_btc.quantize(Decimal(10) ** -4, rounding=ROUND_DOWN)
                    
                    debugger.debug(Msg.Debug.TRADABLE_BTC.format(tradable_btc=tradable_btc))
                    debugger.debug(Msg.Debug.TRADABLE_ASK_BID.format(
                        from_exchange=self.secondary_exchange_str,
                        from_orderbook=secondary_orderbook[currency],
                        to_exchange=self.primary_exchange_str,
                        to_orderbook=primary_orderbook[currency]
                        
                    ))
                except:
                    debugger.exception(Msg.Error.FATAL)

                if max_profit is None and (tradable_btc != 0 or alt_amount != 0):
                    max_profit = [btc_profit, tradable_btc, alt_amount, currency, trade]
                elif max_profit is None:
                    continue
                elif max_profit[0] < btc_profit:
                    max_profit = [btc_profit, tradable_btc, alt_amount, currency, trade]
                    #  최고 이익일 경우, 저장함

                self.collected_data = {
                    'user_id': self.email,
                    'profit_percent': real_diff,
                    'profit_btc': btc_profit,
                    'current_time': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                    'primary_market': self.primary_exchange_str,
                    'secondary_market': self.secondary_exchange_str,
                    'coin_name': currency  # currency
                }

        return max_profit

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

# init 단으로 옮기는 것을 고려해 볼것 #

# --- Outer Import Modules ---
from PyQt5.QtCore import pyqtSignal, QThread
from telegram import Bot
# --- END ---

# --- Inner Import Modules ---
from decimal import Decimal, ROUND_DOWN
from datetime import datetime

import asyncio
# --- END ---

# --- SAI Import Modules ---
from pyinstaller_patch import *

from Bithumb.bithumb import Bithumb
from Binance.binance import Binance
from Bitfinex.bitfinex import Bitfinex
from Upbit.upbit import UpbitBTC, UpbitUSDT, UpbitKRW
from Huobi.huobi import Huobi

import .settings
# --- END ---


class TradeThread(QThread):
    class TradeThread(QThread):
        log_signal = pyqtSignal(int, str)
        stopped = pyqtSignal()
        profit_signal = pyqtSignal(str, float)
        
    def __init__(self, email, primary_info, secondary_info, min_profit_per, min_profit_btc, auto_withdrawal):
        '''
        :param email: 이메일
        :param primary_info: 첫번쨰 거래소의 정보들
        :param secondary_info: 두번째 거래소 정보들
        :param min_profit_per: 최소 이익 퍼센트
        :param min_profit_btc: 최소 이익 BTC
        :param auto_withdrawal: 자동 출금 여부
        '''
        
        super().__init__()
        self._stop_flag = True
        self.email = email
        self.min_profit_per = min_profit_per
        self.min_profit_btc = min_profit_btc
        self.auto_withdrawal = auto_withdrawal

        self.primary_name = list(primary_info.keys())[0]
        self.secondary_name = list(secondary_info.keys())[0]

        self.primary_cfg = primary_info[self.primary_name]
        self.secondary_cfg = secondary_info[self.secondary_name]

        self.primary = None
        self.secondary = None
        self.primary_balance = None
        self.secondary_balance = None
        self.collected_data = {}
        
        self.sai_profit_save_url = 'http://www.saiblockchain.com/api/pft_data'
        
    def stop(self):
        self._stop_flag = True
    
    def run(self):
        exchanges = []
        self.primary = self.get_exchange(self.primary.NAME, self.primary_cfg)
        if not self.primary:
            self.stop()
            self.stopped.emit()
            return
        self.secondary = self.get_exchange(self.secondary.NAME, self.secondary_cfg)
        if not self.secondary:
            self.stop()
            self.stopped.emit()
            return

        self._stop_flag = False
        try:
            self.log_signal.emit(logging.INFO, "최소 %: {}%".format(self.min_profit_per))
            self.min_profit_per /= 100.0
            self.log_signal.emit(logging.INFO, "최소 btc: {}BTC".format(self.min_profit_btc))
            self.log_signal.emit(logging.INFO, "자동 출금: {}".format(self.auto_withdrawal))
        except:
            self.log_signal.emit(logging.INFO, "잘못된 값이 설정되어 있습니다. 설정값을 확인해주세요")
            self.stop()
            self.stopped.emit()
            return

        self.log_signal.emit(logging.INFO, "자동 차익매매 감지 시작")
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.trader())
            loop.close()
        except:
            debugger.exception("FATAL")
            return False
        
        self.stop()
        self.stopped.emit()
    
    def _is_validate_telegram_token(self, upbit, telegram_key):
        """
        :param upbit: upbit object
        :param telegram_key: telegram_key
        :return: True if telegram_key is right key else False
        """
        try:
            upbit.bot = Bot(telegram_key)
            return True
        except:
            return False
        
    def _is_validate_telegram_chat_id(self, telegram, telegram_id):
        """
        :param telegram: telegram bot object
        :param telegram_id: telegram_id
        :return: True if chat id is exist else False
        """
        try:
            telegram.get_chat(telegram_id)
            return True
        except:
            self.log_signal.emit(logging.INFO,
                                 ("존재하지 않는 채팅 아이디 입니다.\n"
                                  "채팅 아이디가 올바르다면 봇에게 메세지를 보낸 후 다시 시도해 주세요."))
            return False

    def get_exchange(self, exchange_name, cfg):
        """
        :param exchange_name: 입력받을 객체 이름
        :param cfg: key, secret등 객체저장에 필요한 정보
        :return: Exchange 객체
        """
        key, secret = cfg['key'], cfg['secret']
        if exchange_name == 'Bithumb':
            return Bithumb(key, secret)
        elif exchange_name == 'Binance':
            exchange = Binance(key, secret)
            # binance는 최초 1회 Exchange_info()를 실행해야 함.
            exchange.get_exchange_info()
        elif exchange_name == 'Bitfinex':
            return Bitfinex(key, secret)
        elif exchange_name == 'Huobi':
            exchange = Huobi(key, secret)
            # Huobi는 최초 1회 get_account_id를 해야 함
            exchange.get_account_id()
        elif 'Upbit' in exchange_name:
            id_, pw, tkey, tchatid = cfg['id'], cfg['pw'], cfg['tkey'], cfg['tchatid']
            if 'KRW' in exchange_name:
                exchange = UpbitKRW(id_, pw, tkey, tchatid)
            elif 'USDT' in exchange_name:
                exchange = UpbitUSDT(id_, pw, tkey, tchatid)
            elif 'BTC' in exchange_name:
                exchange = UpbitBTC(id_, pw, tkey, tchatid)
            else:
                self.log_signal.emit(logging.DEBUG, "Upbit내부에 있는 객체가 아닙니다. [{}]".format(exchange_name))
                return False
            
            if not self._is_validate_telegram_token(exchange, tkey):
                self.log_signal.emit(logging.INFO, "잘못된 텔레그램 봇 토큰입니다.")
                return False
                
            if not self._is_validate_telegram_chat_id(exchange.bot, tchatid):
                self.log_signal.emit(logging.INFO,
                                     ("존재하지 않는 채팅 아이디 입니다.\n"
                                      "채팅 아이디가 올바르다면 봇에게 메세지를 보낸 후 다시 시도해 주세요."))
            
            # <--- 여기 부분은 업비트로 가야할거 같은뎅 --->
            self.log_signal.emit(logging.INFO, "[{}] 업비트 인증을 시작합니다.".format(exchange.NAME))
            if 'pydevd' in sys.modules:
                exchange.chrome(headless=False)
            else:
                exchange.chrome(headless=True)
            while True:
                success, tokens, msg, st = exchange.sign_in(id_, pw)
                if not tokens:
                    self.log_signal.emit(logging.INFO, '')
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
        # <-------------------->
        else:
            self.log_signal.emit(logging.DEBUG, "올바른 객체를 입력받지 않았습니다. [{}]".format(exchange_name))
            return False
        
    def _get_precision(self, currency):
        """
        코인 최소 매매 단위 체크함수
        :param exchange: 거래소 obj
        :param currency: coin
        :return: btc, alt precision, 단 거래소 중 단위가 큰 값을 우선해서 리턴
        """
        pry_suc, pry_precision, pry_msg, pry_time  = self.primary.get_precision(currency)
        sec_suc, sec_precision, sec_msg, sec_time = self.secondary.get_precision(currency)
        
        is_success = (pry_suc and sec_suc)
        
        if not is_success:
            [self.log_signal.emit(logging.INFO, msg) for msg in (pry_msg, sec_msg) if msg]
            time.sleep(max(pry_time, sec_time))
            return False
        
        pry_btc_precision, pry_alt_precision = pry_precision
        sec_btc_precision, sec_alt_precision = sec_precision
        
        btc_precision = max(pry_btc_precision, sec_btc_precision)
        alt_precision = max(pry_alt_precision, sec_alt_precision)

        return btc_precision, alt_precision
    
    def _default_btc_settings(self):
        """
            양쪽 거래소에 BTC가 있는지 확인하는 함수.
            양쪽 거래소는 BTC를 가지고 있어야 프로그램 실행이 가능함.
        :return: default_btc * 1.5 if exist_btc else None
        """
        empty_exchange_list = []
        
        if not 'BTC' in self.primary_balance :
            empty_exchange_list.append(self.primary.NAME)
        elif not 'BTC' in self.secondary_balance:
            empty_exchange_list.append(self.secondary.NAME)
        if empty_exchange_list:
            self.log_signal.emit(logging.INFO, "거래소 {}에 BTC가 없습니다.".format(empty_exchange_list))
            return None
            
        default_btc = max(self.primary_balance['BTC'], self.secondary_balance['BTC'])
        if not default_btc:
            self.log_signal.emit(logging.INFO, '거래소 {}에 BTC 잔고가 없습니다.'.format([self.primary.NAME, self.secondary.NAME]))
            return None
        
        return default_btc * 1.5
    
    def _able_trading_exchange_validator(self, trading_type):
        """
        :param trading_type: main to sub or sub to main
        :return: type에 대해 거래가 가능하면 True 이외는 False
        """
        if self.primary_name == 'Korbit' and trading_type == 'm_to_s':
            # 코빗은 현재 s_to_m만 지원하고 있는 상태임.
            return False
        return True
        
    def _is_exist_balance_validator(self, alt):
        """
        :param alt: XRP, ETH ...
        :return: 잔고있으면 True 그 외 False
        """
        balance_empty_list = []
        
        if alt not in self.primary_balance.keys() or not self.primary_balance[alt]:
            balance_empty_list.append(self.primary.NAME)
        
        if alt not in self.secondary_balance.keys() or not self.secondary_balance[alt]:
            balance_empty_list.append(self.secondary.NAME)
        
        if balance_empty_list:
            self.log_signal.emit(logging.INFO, '[거래불가]{} {} 잔고가 없습니다.'.format(balance_empty_list, alt))
            return False
        
        return True
        
    
    def _fee_calculator(self, *args):
        """
        :param args: alt 출금비용 & 가격 & btc 출금비용
        :return:
        """
        alt_tx_fee, alt_price, btc_tx_fee = args
        
        return Decimal(alt_tx_fee * alt_price) - Decimal(btc_tx_fee)
        
    def get_max_profit(self, data, currencies, fees, fee_cnt):
        """
        :param data: 거래소 간 orderbook data
        :param currencies: 거래소 간 intersection currencies
        :param fees: 거래소 간 거래&출금 수수료
        :param fee_cnt: 거래 수수료를 몇번 하는지에 대한 COUnt
        :return: 거래소 간 거래 비교 후 가장 큰 차익을 내는 거래소의 각종 데이터들
        """
        primary_trade_fee, secondary_trade_fee, primary_tx_fee, secondary_tx_fee = fees
        primary_fee_cnt, secondary_fee_cnt = fee_cnt
        max_profit = None
        primary_orderbook, secondary_orderbook, data = data

        
        if isinstance(self.min_profit_per, str):
            self.log_signal.emit(logging.INFO, "예상 차익 퍼센트는 실수여야만 합니다.")
            return False

        trading_type = ['m_to_s', 's_to_m']
        for type_ in trading_type:
            if not self._able_trading_exchange_validator(type_):
                continue
            
            for currency in currencies:
                alt = currency.split('_')[1]
                pry_orderbook, sec_orderbook = primary_orderbook[currency], secondary_orderbook[currency]
                
                if not self._is_exist_balance_validator(alt):
                    continue
                
                if data[type_][currency] < self.min_profit_per:
                    continue
                
                expected = data[type_][currency] * 100
                if trade == 'm_to_s':
                    self.log_signal.emit(logging.INFO, '[{} {}->{}] 예상 차익: {} %'.format(currency, self.primary.NAME, self.secondary.NAME, expected))
                    self.log_signal.emit(logging.DEBUG, '[{}] {} ask: {}, {} bids: {}'.format(currency, self.primary_name, pry_orderbook['asks'],
                                                                               self.secondary.NAME, sec_orderbook['bids']))
                else:
                    self.log_signal.emit(logging.INFO, '[{} {}->{}] 예상 차익: {} %'.format(currency, self.secondary.NAME, self.primary.NAME, expected))
                    self.log_signal.emit(logging.DEBUG, '[{}] {} ask: {}, {} bids: {}'.format(currency, self.secondary.NAME,
                                             sec_orderbook['asks'], self.primary.NAME, primary_orderbook['bids']))
                    
                res = self._get_precision(currency)
                
                if not res:
                    continue
                    
                real_diff = ((1 + data[type_][currency]) * ((1 - primary_trade_fee) ** primary_fee_cnt) * (
                        (1 - secondary_trade_fee) ** secondary_fee_cnt)) - 1

                btc_precision, alt_precision = res
                if type_ == 'm_to_s':
                    # 거래소 1에서 ALT를 사고 거래소2에서 ALT를 판다.
                    buy_alt_exchange_balance = self.primary_balance['BTC']
                    buy_alt_exchange_orderbook = primary_orderbook[currency]
                    
                    sell_alt_exchange_balance = self.secondary_balance[alt]
                    sell_alt_exchange_orderbook = secondary_orderbook[currency]
                    
                    buy_alt_exchange_name = self.primary.NAME
                    sell_alt_exchange_name = self.secondary.NAME
                    
                    calculated_fee = self._fee_calculator(primary_tx_fee[alt], primary_orderbook['asks'], secondary_tx_fee['BTC'])
                    
                else:
                    # 거래소 1에서 ALT를 팔고 거래소 2에서 ALT를 산다.
                    buy_alt_exchange_balance = self.secondary_balance['BTC']
                    buy_alt_exchange_orderbook = secondary_orderbook[currency]

                    sell_alt_exchange_balance = self.primary_balance[alt]
                    sell_alt_exchange_orderbook = primary_orderbook[currency]
                    
                    buy_alt_exchange_name = self.secondary.NAME
                    sell_alt_exchange_name = self.primary.NAME
                    
                    calculated_fee = self._fee_calculator(secondary_tx_fee[alt], secondary_orderbook['asks'], secondary_tx_fee['BTC'])

                tradable_btc, alt_amount = self.find_min_balance(buy_alt_exchange_balance, sell_alt_exchange_balance,
                                                     sell_alt_exchange_orderbook, currency, btc_precision, alt_precision)

                btc_profit = (tradable_btc * Decimal(real_diff)) - Decimal(calculated_fee)
                tradable_btc = tradable_btc.quantize(Decimal(10) ** -4, rounding=ROUND_DOWN)
                self.log_signal.emit(logging.DEBUG, 'actual trading btc: {}'.format(tradable_btc))

                self.log_signal.emit(logging.INFO, '[{}] 거래 가능: {} {} {} / {} {} BTC'.format(alt, buy_alt_exchange_name, alt_amount, alt,
                                     sell_alt_exchange_name, tradable_btc))

                self.log_signal.emit(logging.INFO, '[{}] {} -> {} 수익: {} BTC / {} %'.format(alt, buy_alt_exchange_name, sell_alt_exchange_name,
                                     btc_profit, real_diff * 100))

                self.log_signal.emit(logging.DEBUG, 'tradable bids/asks: {}: {} {}: {}'.format(sell_alt_exchange_name, sell_alt_exchange_orderbook,
                                                                                buy_alt_exchange_name, buy_alt_exchange_orderbook))

                if max_profit is None and (tradable_btc != 0 or alt_amount != 0):
                    max_profit = [btc_profit, tradable_btc, alt_amount, currency, type_]
                elif max_profit is None:
                    continue
                elif max_profit[0] < btc_profit:
                    max_profit = [btc_profit, tradable_btc, alt_amount, currency, type_]

                self.collected_data = {
                    'user_id': self.email,
                    'profit_percent': real_diff,
                    'profit_btc': btc_profit,
                    'current_time': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                    'primary_market': self.primary.NAME,
                    'secondary_market': self.secondary.NAME,
                    'coin_name': currency
                }
            
            return max_profit
        
    def _save_profit_expected(self, profits, currencies):
        """
        :param profits: 예상차익
        :param currencies: 거래될 코인종류
        :return: Boolean
        """
        #   m_to_s, s_to_m 정보가 담긴 딕셔너리만 보낸다. 0: primary orderbook, 1: secondary orderbook
        profit = profits[2]
        try:
            r = requests.get("http://saiblockchain.com/api/expected_profit",
                             json={'profit': profit, 'currencies': currencies, 'primary': self.primary.NAME,
                                   'secondary': self.secondary.NAME})
            if r.status_code == 200:
                return True
            else:
                return False
        except:
            debugger.exception("예상차익 저장에러!")
            return False

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


    async def _balance_and_currencies(self):
        """
            잔고 확인 및 balance self 변수에 넣는 함수
            :return: 거래 가능한 currencies들을 BTC_XXX로 리스트 리턴
            
        """
        if DEBUG:
            pry_balance = {'BTC': 0.4, 'ETH': 10, 'BCC': 7, 'LTC': 55, 'XRP': 10000,
                               'ETC': 262, 'OMG': 1000, 'DASH': 1.5, 'XMR': 37, 'ADA': 55000,
                               'QTUM': 500, 'ZEC': 19, 'EOS': 1000, 'BTG': 200}
            sec_balance = {'BTC': 0.4, 'ETH': 10, 'BCH': 7, 'LTC': 55, 'XRP': 10000,
                                 'ETC': 262, 'OMG': 1000, 'DASH': 1.5, 'XMR': 37,
                                 'QTUM': 500, 'ZEC': 19, 'BTG': 200}

        else:
            res = await asyncio.gather(self.primary.balance(), self.secondary.balance())
            pry_res, sec_res = res
            
            pry_suc, pry_balance, pry_msg, pry_time = pry_res
            sec_suc, sec_balance, sec_msg, sec_time = sec_res
            
            if not pry_suc:
                self.log_signal.emit(logging.INFO, pry_msg)
            if not sec_suc:
                self.log_signal.emit(logging.INFO, sec_msg)
            
            is_success = (pry_suc, sec_suc)
            
            if not is_success:
                time.sleep(max(pry_time, sec_time))
                return False
        
        if self.primary_balance != pry_balance or self.secondary_balance != sec_balance:
            self.log_signal.emit(logging.INFO, '[{} 잔고] {}'.format(self.primary.NAME, pry_balance))
            self.log_signal.emit(logging.INFO, '[{} 잔고] {}'.format(self.secondary.NAME, sec_balance))

            self.primary_balance = pry_balance
            self.secondary_balance = sec_balance
            
        currencies = list(set(sec_balance).intersection(pry_balance))
        self.log_signal.emit(logging.DEBUG, 'tradable coins: {}'.format(currencies))

        attached_currencies = ['BTC_' + coin for coin in currencies if not coin == 'BTC']

        return attached_currencies

    async def _deposits(self):
        """
            거래소들의 입금주소 address 가져오는 함수
            :return: 입금 주소 리스트들  if success else False
        """
        self.log_signal.emit(logging.INFO, "출금정보를 가져오는 중입니다...")
        
        pry_res, sec_res = await asyncio.gather(self.primary.get_deposit_addrs(),
                                                self.secondary.get_deposit_addrs())
        
        pry_suc, pry_data, pry_msg, pry_time = pry_res
        sec_suc, sec_data, sec_msg, sec_time = pry_res
        
        if not pry_suc:
            self.log_signal.emit(logging.INFO, pry_msg)
        if not sec_suc:
            self.log_signal.emit(logging.INFO, sec_msg)
            
        is_success = (pry_suc and sec_suc)
        max_ts = max(pry_time, sec_time)
        
        if is_success:
            self.log_signal.emit(logging.INFO, "출금정보 추출 완료.")
            return pry_data, sec_data
        
        else:
            self.log_signal.emit(logging.INFO,
                                 "출금정보 추출 실패. 출금 정보 확인 후 다시 시작해 주세요.")
            time.sleep(max_ts)
            return False
        
    async def _fees(self, exchange):
        fut = [
            exchange.get_trading_fee(),
            exchange.get_transaction_fee(),
        ]
        td_fees, tx_fees = await asyncio.gather(*fut)

        td_suc, td_data, td_msg, td_time = td_fees
        tx_suc, tx_data, tx_msg, tx_time = tx_fees

        if not td_suc:
            self.log_signal.emit(logging.INFO, td_msg)

        if not tx_suc:
            self.log_signal.emit(logging.INFO, tx_msg)

        ts = max(td_time, tx_time)
        
        is_success = (td_suc and tx_suc)
        
        if not is_success:
            time.sleep(ts)
            return False
        else:
            self.log_signal.emit(logging.DEBUG, "수수료 조회 성공")
            return td_data, tx_data

    async def trader(self):
        deposit = await self._deposits()
        if self.auto_withdrawal:
            if not deposit:
                return False
        fee_cnt = (self.primary.fee_count(), self.secondary.fee_count())
        refreshed = 0
        while evt.is_set() and not self.stop_flag:
            if time.time() >= refreshed + 600:
                fees = [await self._fees(exchange) async for exchange in self.exchanges]
                if not fees:
                    #   실패 했을 경우 다시 요청
                    continue
                refreshed = time.time()

            currencies = await self._balance_and_currencies()
            
            if not self.primary_balance or not self.secondary_balance:
                continue
            
            elif not currencies:
                continue
                
            default_btc = self._default_btc_settings()
            
            if default_btc is None:
                continue

            self.log_signal.emit(logging.DEBUG, "orderbook 호출")
            
            # 해당 위치에 있는게 적절한지 재고
            success, data, msg, time_ = await self.primary.compare_orderbook(
                self.secondary, currencies, default_btc
            )
            if not success:
                self.log_signal.emit(logging.INFO, msg)
                time.sleep(time_)
                continue

            # btc_profit, tradable_btc, alt_amount, currency, trade
            max_profit = self.get_max_profit(data, currencies, fees, fee_cnt)
            if max_profit is None:
                self.log_signal.emit(logging.INFO, "만족하는 조건을 찾지 못하였습니다. 조건 재검색...")
                self._save_profit_expected(data, currencies, self.primary.NAME, self.secondary.NAME)
                continue
            elif max_profit is False:
                # 예상차익이 실수가 아닌경우
                continue

            btc_profit = max_profit[0]

            if DEBUG:
                self.log_signal.emit(logging.INFO, "디버그 모드")
                try:
                    bot = Bot(token='607408701:AAGYRRnzUKTWRIdJvYzl8AQMlGz52vinoUA')
                    bot.get_chat('348748653')
                    bot.sendMessage('348748653',
                                    '[{}] {} - {}: {}'.format(currencies, self.primary.NAME, self.secondary.NAME, data))
                except:
                    self.log_signal.emit(logging.INFO, "텔레그램 메세지 전송 실패")

            if btc_profit >= self.min_profit_btc:
                success, res, msg, st = self.trade(max_profit, deposit, fees)

                requests.post(sai_url, data=self.collected_data)
                self._save_profit_expected(data, bal_n_crncy[2], self.primary.NAME,
                                                    self.secondary.NAME)
            
                if not success:
                    self.log_signal.emit(logging.INFO, "거래에 실패하였습니다. 처음부터 다시 진행합니다." )
                    self.log_signal.emit(logging.DEBUG, "내용: [{}]".format(msg))
                    continue

                self.log_signal.emit(logging.INFO, "차익거래에 성공했습니다.")
            
            else:
                #   사용자 지정 BTC 보다 적은경우
                self.log_signal.emit(logging.INFO,
                                     "최고 이익이 사용자 지정 BTC 보다 작아 거래하지 않습니다.")
                self._save_profit_expected(data, currencies)

    def _is_exist_deposit_addrs_checker(self, addrs, coin):
        return True if coin in addrs and addrs[coin] else False
        
    def withdraw_trigger(self, *args):
        coin, btc_send_amount, send_amount, buy_coin_exchange, sell_coin_exchange, buy_coin_addr, sell_coin_addrs = args
        
        if self._is_exist_deposit_addrs_checker(sell_coin_addrs, coin):
            if coin in settings.USE_TAG_COINS:
                tag = coin + 'TAG'
                
                if self._is_exist_deposit_addrs_checker(sell_coin_exchange, tag):
                    return buy_coin_exchange.withdraw(coin, send_amount, sell_coin_addrs[coin],
                             sell_coin_addrs[tag])
            else:
                return buy_coin_exchange.withdraw(coin, send_amount, sell_coin_addrs[coin])
        
        self.log_signal.emit(logging.INFO, '{}의 {}주소가 없습니다. 아래 안내대로 수동 이체해주세요.'.format(
            sell_coin_exchange.NAME, coin))
        self.log_signal.emit(logging.INFO, '{}->{} {} {} 만큼 이동'.format(buy_coin_exchange.NAME, sell_coin_exchange.NAME,
                                                                       coin, send_amount))

        self.log_signal.emit(logging.INFO,
                             '{} -> {} BTC {} 만큼 이동'.format(sell_coin_exchange.NAME, buy_coin_exchange.NAME, send_amount))

        return True, '', 'address_not_exist', 0
    
    def buy_sell_alt_trader(self, *args):
        buy_alt_exchange, sell_alt_exchange, max_profit, buy_alt_fees = args
        
        buy_alt_td_fee, buy_alt_tx_fee = buy_alt_fees
        
        btc_profit, tradable_btc, alt_amount, currency, trade = max_profit
        alt = currency.split('_')[1]
        
        
        #   거래소1 에서 ALT 를 사고(btc를팔고) 거래소2 에서 BTC 를 사서(ALT를팔고) 교환함
        success, res, msg, time_ = buy_alt_exchange.base_to_alt(currency, tradable_btc, alt_amount, buy_alt_td_fee,
                                                                buy_alt_tx_fee)
        
        if not success:
            return False, '', msg, time_
        
        self.log_signal.emit(logging.DEBUG, "{}: {} 구입".format(buy_alt_exchange.NAME, alt))

        alt_amount = res
        sell_alt_exchange.alt_to_base(currency, tradable_btc, alt_amount)
        
        self.log_signal.emit(logging.DEBUG, '{}: {} 판매'.format(sell_alt_exchange.NAME, alt))
        
        send_amount = alt_amount + Decimal(buy_alt_tx_fee[alt]).quantize(Decimal(10) ** alt_amount.as_tuple().exponent)
        
        if 'Upbit' in buy_alt_exchange.NAME and 'Upbit' in sell_alt_exchange.NAME:
            return True, '', '', 0
        
        return True, float(send_amount), '', 0
        
    def trade(self, max_profit, deposit_addrs, fee):
        """
        :param max_profit:
        :param deposit_addrs:
        :param fee:
        :return:
        """
        self.log_signal.emit(logging.INFO, "최대 이윤 계산결과가 설정한 지정 BTC 보다 높습니다.")
        self.log_signal.emit(logging.INFO, "거래를 시작합니다.")
        primary_td_fee, secondary_td_fee, primary_tx_fee, secondary_tx_fee = fee
        primary_deposit_addrs, secondary_deposit_addrs = deposit_addrs
        
        if self.auto_withdrawal:
            if not primary_deposit_addrs or not secondary_deposit_addrs:
                return False, '', '메인 또는 서브 거래소 입금주소가 존재하지 않습니다', 0
        
        btc_profit, tradable_btc, alt_amount, currency, trade = max_profit
        alt = currency.split('_')[1]
        if trade == 'm_to_s':
            buy_alt_fees = (primary_td_fee, primary_tx_fee)
            success, send_amount, msg, time_ = self.buy_sell_alt_trader(self.primary, self.secondary, max_profit, buy_alt_fees)

            btc_send_amount = tradable_btc + Decimal(secondary_tx_fee['BTC']).quantize(
                Decimal(10) ** tradable_btc.as_tuple().exponent)

            if not success:
                return False
            
            if self.auto_withdrawal:
                while not self._stop_flag:
                    # 거래소1 -> 거래소2 ALT 이체
                    success, data, msg, time_ = self.withdraw_trigger(alt, btc_send_amount, send_amount, self.primary, self.secondary, primary_deposit_addrs,
                                                   secondary_deposit_addrs)
                    
                    if success:
                        if 'address_not_exist' in msg:
                            self.stop()
                            return True, '', '', 0
                    
                    else:
                        self.log_signal.emit(logging.INFO, '{}: {} 이체에 실패했습니다. 에러가 계속되면 중지해주세요.'.format(self.primary.NAME, alt))
                        self.log_signal.emit(logging.DEBUG, '내용: [{}]'.format(msg))
                        continue
                        
                    break
                    
                while not self._stop_flag:
                    # 거래소2 -> 거래소1 BTC 이체
                    success, data, msg, time_ = self.withdraw_trigger('BTC', btc_send_amount, send_amount, self.secondary, self.primary, secondary_deposit_addrs,
                                                                     primary_deposit_addrs)
    
                    if success:
                        if 'address_not_exist' in msg:
                            self.stop()
                            return True, '', '', 0
    
                    else:
                        self.log_signal.emit(logging.INFO, '{}: BTC 이체에 실패했습니다. 에러가 게/속되면 중지해주세요.'.format(self.secondary.NAME))
                        self.log_signal.emit(logging.DEBUG, '내용: [{}]'.format(msg))
                        continue
                        
                    break
            
            else:
                self.log_signal.emit(logging.INFO, "수동 이체 상태입니다. 아래 안내대로 수동 이체해주세요.")
                self.log_signal.emit(logging.INFO, '{}->{} {} {} 만큼 이동'.format(self.primary.NAME, self.secondary.NAME, alt, send_amount))
                self.log_signal.emit(logging.INFO, '{}->{} BTC {} 만큼 이동'.format(self.secondary.NAME, self.primary.NAME, btc_send_amount))
                
            self.log_signal.emit(logging.INFO, "거래가 완료되었습니다. 수동이체 후 다시 시작해주세요.")
            self.stop()
            
        else:
            buy_alt_fees = (secondary_td_fee, secondary_tx_fee)
            
            success, send_amount, msg, time_ = self.buy_sell_alt_trader(self.secondary, self.primary, max_profit, buy_alt_fees)
            
            btc_send_amount = tradable_btc + Decimal(primary_tx_fee['BTC']).quantize(
                Decimal(10) ** tradable_btc.as_tuple().exponent)

            if not success:
                return False
            
            if self.auto_withdrawal:
                while not self._stop_flag:
                    # 거래소2 -> 거래소1 ALT 이체
                    success, data, msg, time_ = self.withdraw_trigger(alt, btc_send_amount, send_amount, self.secondary, self.primary, secondary_deposit_addrs,
                                                   primary_deposit_addrs)
                    if success:
                        if 'address_not_exist' in msg:
                            self.stop()
                            return True, '', '', 0

                    else:
                        self.log_signal.emit(logging.INFO, '{}: {} 이체에 실패했습니다. 에러가 계속되면 정지해주세요.'.format(self.secondary.NAME, alt))
                        self.log_signal.emit(logging.INFO, '내용: [{}]'.format(msg))
                        continue

                    break

                while not self._stop_flag:
                    # 거래소1 -> 거래소2 BTC 이체
                    success, data, msg, time_ = self.withdraw_trigger('BTC', btc_send_amount, send_amount,
                                                                      self.primary, self.secondary,
                                                                      primary_deposit_addrs,
                                                                      secondary_deposit_addrs)
                    if success:
                        if 'address_not_exist' in msg:
                            self.stop()
                            return True, '', '', 0

                    else:
                        self.log_signal.emit(logging.INFO, '{}: {} 이체에 실패했습니다. 실패가 계속되면 정지해주세요.'.format(self.primary.NAME, alt))
                        self.log_signal.emit(logging.DEBUG, '내용: [{}]'.format(msg))
                        continue

                    break

            else:
                self.log_signal.emit(logging.INFO, "수동 이체 상태입니다. 아래 안내대로 수동 이체해주세요.")
                self.log_signal.emit(logging.INFO, '{}->{} {} {} 만큼 이동'.format(self.secondary.NAME, self.primary.NAME, alt, send_amount))
                self.log_signal.emit(logging.INFO, '{}->{} BTC {} 만큼 이동'.format(self.primary.NAME, self.secondary.NAME, btc_send_amount))

            self.log_signal.emit(logging.INFO, "거래가 완료되었습니다. 수동이체 후 다시 시작해주세요.")
            self.stop()

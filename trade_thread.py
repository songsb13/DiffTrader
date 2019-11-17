
# init 단으로 옮기는 것을 고려해 볼것 #
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
# <--- IMPORT --->


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
        
    def stop(self):
        self._stop_flag = True
    
    def run(self):
        exchanges = []
        for
        
        
        self.primary = self.get_exchange(self.primary_exchange_str, self.primary_cfg)
        if not self.primary:
            self.stop()
            self.stopped.emit()
            return
        self.secondary = self.get_exchange(self.secondary_exchange_str, self.secondary_cfg)
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

            self.log_signal.emit(logging.INFO, "[{}] 업비트 인증을 시작합니다.".format(exchange_str))
            if 'pydevd' in sys.modules:
                exchange.chrome(headless=False)
            else:
                exchange.chrome(headless=True)
            while True:
                success, tokens, msg, st = exchange.sign_in(id_, pw)
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
        else:
            self.log_signal.emit(logging.DEBUG, "올바른 객체를 입력받지 않았습니다. [{}]".format(exchange_name))
            return False

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
        
        if not pry_res:
            self.log_signal.emit(logging.INFO, pry_msg)
        if not sec_res:
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
            return td_data, tx_data

    async def trader(self):
        deposit = await self._deposits()
        if self.auto_withdrawal:
            if not deposit:
                return False
        fees = [await self._fees(exchange) async for exchange in self.exchanges]
        
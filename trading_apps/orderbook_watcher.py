from trading_apps.profit_validator import ProfitValidator


class OrderbookWatcher(object):
	log_signal = pyqtSignal()
	
	def __init__(self, exchanges, websocket, input_currencies, lock_container):
		self._exchange = exchanges[0]
		self._other_exchanges = exchanges[1:]
		
		self._exchange_ws = websocket
		
		self._lock_container = lock_container

		self._watch_currencies = input_currencies
		self._is_thread_running_flag = {exchange.NANE: {currency: False for currency in input_currencies} for exchange in exchanges}
		
		self._stop_flag = False
		self._price_dic = {}
		
		self._exchange_ws = self._exchange.websocket()
		
		self._log_header = '[{}]OrderbookWatcher:: '.format(self._exchange.NAME)
	
	def run(self):
		while not self._stop_flag:
			try:
				self.get_current_price()
			except:
				debugger.exception(self._log_header + 'FATAL')
	
	def stop(self):
		self._stop_flag = True
		self.log_signal.emit(logging.DEBUG, self._log_header + 'STOP')
	
	def trading_thread_done(self, exchange, market):
		self._is_thread_running_flag[exchange][market] = False
		
	def _is_price_changed_checker(self, *args):
		"""
			args:
			- market: KRW-BTC
			- trade_price: market의 현재 가격, decimal
			- price_dic: 이전 저장된 market 값과 동일한지 여부확인을 위한 dict.

			:return: price_dic에 값이 없거나 trade_price의 값이 변경된게 감지되면 True
			그 외는 False
		"""
		self.log_signal.emit(logging.DEBUG, self._log_header + 'is_price_changed_checker param={}'.format(args))
		market, trade_price, price_dic = args
		return True if market not in price_dic or price_dic[market] != trade_price \
			else False
	
	def _running_check(self, exchange_name, coin):
		"""
		:param exchange_name: upbit, binance..
		:param coin: coin name
		:return: True if already running else False
		"""
		is_running = self._is_thread_running_flag[exchange_name][coin]
		
		self.log_signal.emit(logging.DEBUG, self._log_header + 'running_check param=[{}]'.format(
			is_running))
		return is_running
	
	def _run_other_exchanges(self, market):
		"""
			:param market: BTC_XXX sai market symbol
		"""
		self.log_signal.emit(logging.DEBUG, self._log_header + 'Start run_other_exchanges'.format(market))
		for other in self._other_exchanges:
			if not self._running_check(other.NAME, market):
				self.log_signal.emit(logging.DEBUG, self._log_header + 'main[{}] sub[{}] market[{}] START!!'.
									 format(self._exchange.NAME, other.NAME, market))
				ProfitValidator(self._exchange, other, market, self._lock_container[self._exchange.NAME][other.NAME])
				self._is_thread_running_flag[other][market] = True
	
	def get_current_price(self):
		"""
			websocket 연결 후 가격이 변하는지 감지하는 함수.
			변화가 감지되면 block 상태인 특정 마켓 surveillance_thread Q에 price를 넣어서 실행한다.
		"""
		
		self.log_signal.emit(logging.DEBUG, self._log_header + 'Start get_current_price')
		market_price_data_set = self._exchange_ws.request_all_market_price_data(self._watch_currencies)
		for market, trade_price in market_price_data_set.items():
			if self._is_price_changed_checker(market, trade_price, self._price_dic):
				self._price_dic[market] = trade_price
				self._run_other_exchanges(market)
from trading_apps import *
from trading_apps.profit_validator import ProfitValidator


class OrderbookWatcher(object):
	log_signal = pyqtSignal()
	
	def __init__(self, exchanges, input_currencies, lock_container):
		self._exchange = exchanges[0]
		self._other_exchanges = exchanges[1:]

		self._lock_container = lock_container

		self._watch_currencies = input_currencies
		self._is_already_thread_running_flag = {exchange.NANE: {currency: False for currency in input_currencies} for exchange in exchanges}
		
		self._stop_flag = False
		
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
	
	def get_current_price(self):
		"""
			websocket 연결 후 가격이 변하는지 감지하는 함수.
			변화가 감지되면 block 상태인 특정 마켓 surveillance_thread Q에 price를 넣어서 실행한다.
		"""
		
		self.log_signal.emit(logging.DEBUG, self._log_header + 'Start get_current_price')
		
		json_data_ = self.parameter_collecting_by_market_name()
		self._exchange_ws.get_connection()
		self._exchange_ws.send_data(json_data_)

		price_dic = {}
		while not self._stop_flag:
			try:
				raw_data = self._exchange_ws.result_data()
			except WebSocketConnectionClosedException:
				self._exchange_ws.get_connection()
				
				json_data_ = self.parameter_collecting_by_market_name()
				self._exchange_ws.send_data(json_data_)
				raw_data = self._exchange_ws.result_data()
				
			totals = json.loads(raw_data.decode())
			market = totals['code']

			# 변동이 필요함 ( upbit 기준인데 받아오는 데이터가 다를 수 있음 )
			trade_price = totals['trade_price']
			if not self.running_check(self._exchange.NAME, market):
				continue

			if not self.is_price_changed_checker(market, trade_price, price_dic):
				continue

			price_dic[market] = trade_price
			self.log_signal.emit(logging.DEBUG, self._log_header + 'market[{}] Q에 값 [{}]를 넣어서 실행합니다.'.format(market, trade_price))

			for other in self._other_exchanges:
				ProfitValidator('ex1', 'ex2', market, self._lock_container[self._exchange.NAME][other.NAME])
				self._is_already_thread_running_flag[other][market] = True

	def parameter_collecting_by_market_name(self):
		"""
		각 거래소 별 파라메터가 다를 수 있음.
		:return:
		"""
		
		self.log_signal.emit(logging.DEBUG, self._log_header + 'parameter_colleciting_by_market_name')
		exchange_name = self._exchange.NAME.lower()
		if exchange_name == 'upbit':
			market_listing = self._watch_currencies
			data = [{"ticket": "gimo's_ticket"}, {"type": "ticker", "codes": market_listing, "isOnlyRealtime": True}]
		elif exchange_name == 'bithumb':
			pass
		
		elif exchange_name == 'binance':
			pass
		
		else:
			pass
		
		return json.dumps(data).replace(' ', '')

	def is_price_changed_checker(self, *args):
		"""
			args:
			- market: KRW-BTC
			- trade_price: market의 현재 가격, float
			- price_dic: 이전 저장된 market 값과 동일한지 여부확인을 위한 dict.

			:return: price_dic에 값이 없거나 trade_price의 값이 변경된게 감지되면 True
			그 외는 False
		"""
		self.log_signal.emit(logging.DEBUG, self._log_header + 'is_price_changed_checker param={}'.format(args))
		market, trade_price, price_dic = args
		return True if market not in price_dic or price_dic[market] != trade_price \
			else False

	def running_check(self, exchange_name, coin):
		"""
		:param exchange_name: upbit, binance..
		:param coin: coin name
		:return: True if already running else False
		"""
		is_already_running = self._is_already_thread_running_flag[exchange_name][coin]
		
		self.log_signal.emit(logging.DEBUG, self._log_header + 'running_check param=[{}]'.format(is_already_running))
		return is_already_running
		

"""
	OrderbookWatcher
	오더북 감지, 에를들어 3개 거래소로 시작하면 각 exchange object를 받아서 진행 ( a, b, c 거래소 )
	exchange.get_orderbook_with_socket으로 값 가져오면서 변화 감지
	변화 감지되면 Profitvalidator thread 실행 ( ab, ac )
	수익은 한번만 남 ( 가격변화 감지가 없는 한 )
	코인별로 거래소 키면 됨 ab(xrp), ab(eth), ac(xrp), ac(eth)
	lock은 orderbookWatcher 윗단에서 parameter, 거래소 pair로 dict해서 받는다.

"""


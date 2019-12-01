from DiffTrader.trading_apps import *
from DiffTrader.trading_apps.profit_validator import ProfitValidator

class OrderbookWatcher(object):
	log_signal = pyqtSignal()
	
	def __init__(self, exchanges, input_currencies):
		self.log_signal.emit(logging.DEBUG, '[{}]OrderbookWatcher:: INIT START'.format(exchange.NAME))
		self._exchange = exchanges[0]
		self._other_exchanges = exchanges[1:]
		self._watch_currencies = input_currencies
		# self._is_trading_flag = {currency: False for currency in input_currencies}
		self._is_already_thread_running_flag = {exchange.NANE: {currency: False for currency in input_currencies} for exchange in exchanges}
		
		self._stop_flag = False
		
		self._exchange_ws = self._exchange.websocket()
		
		self._log_header = '[{}]OrderbookWatcher:: '.format(exchange.NAME)
	
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
		
		while not self._stop_flag:
			try:
				raw_data = self._exchange_ws.result_data()
			except WebSocketConnectionClosedException:
				self._exchange_ws.get_connection()
				
				json_data_ = self.parameter_collecting_by_market_name()
				self._exchange_ws.send_data(json_data_)
				raw_data = self._exchange_ws.result_data()
				
			totals = json.loads(raw_data.decode())
			
			if self.running_check()
			
			debugger.debug('WebSocketThread::: market[{}] Q에 값 [{}]를 넣어서 실행합니다.'.format(market, trade_price))
			
			thread.lock()
			
			ProfitValidator('ex1', 'ex2', 'coin')

	
	def parameter_collecting_by_market_name(self):
		exchange_name = self._exchange.NAME.lower()
		if exchange_name == 'upbit':
			data = [{"ticket": "gimo's_ticket"}, {"type": "ticker", "codes": market_listing, "isOnlyRealtime": True}]
		elif exchange_name == 'bithumb':
			pass
		
		else:
			pass
		
		return json.dumps(data).replace(' ', '')
	
	def running_check(self, exchange_name, coin):
		return self._is_already_thread_running_flag[exchange_name][coin]
		
		
"""
	1. OrderbookWatcher
	1. 오더북 감지, 에를들어 3개 거래소로 시작하면 각 exchange object를 받아서 진행 ( a, b, c 거래소 )
	2. exchange.get_orderbook_with_socket으로 값 가져오면서 변화 감지
	3. 변화 감지되면 Profitvalidator thread 실행 ( ab, ac )
	4. 만약 trade 진행 중이면 스레드 생성 막는 flag 생성
	5. 수익은 한번만 남 ( 가격변화 감지가 없는 한 )
"""


"""

	debugger.debug('WebSocketThread::: time[{}], market[{}], trade_price[{}]'.
	format(datetime.datetime.now(), market, trade_price))
	if self.start_surveillance_thread_check(market, trade_price, price_dic):
	price_dic[market] = trade_price
	
	debugger.debug('WebSocketThread::: market[{}] Q에 값 [{}]를 넣어서 실행합니다.'.format(market, trade_price))
	self.surve_thread_queue_list[market].put(trade_price)
	
	self.time_refresh_signal.emit()
	
	debugger.debug("WebSocketThread::: Stop Done!")
	
	except Exception as ex:
	debugger.debug('WebSocketThread::: 에러가 발생했습니다 !!! [{}]'.format(ex))
	
"""
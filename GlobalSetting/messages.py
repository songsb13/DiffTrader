"""
Logging Messages
"""

"""
    Logs 정책
    debug들은 내부에서 다 처리하고, 윗단 값들 (trade_thread.py) 등은 debug 최소화.
    대신 info들 노출시켜 주는 것에 중점을 둬야함.
"""


class GlobalMessage(object):
    ENTRANCE = 'parameters={data}'
    FATAL = 'FATAL'


class SetterMessage(object):
    START = 'start setter process, user={}, exchange_str={}'


class MonitoringMessage(object):
    START = 'start monitoring process, primary={}, secondary={}, user={}'
    RUNNING = 'running monitoring process, primary={}, secondary={}, user={}'
    GET_ERROR_MESSAGE_IN_COMPARE = 'get error message in _compare_orderbook. error_message={}'
    BALANCE_NOT_FOUND = '{}, has not {} in currency balance.'
    EXPECTED_PROFIT = "expected profit is not enough to reach setting's profit. {} < {}"
    TRADABLE_INFO = "tradable={}, coin_amount={}, btc_profit={}, real_difference={}"

    FAIL_TO_GET_ORDERBOOK = 'fail to get orderbook data from _compare_orderbook.'
    FAIL_TO_GET_SUITABLE_PROFIT = 'fail to get suitable profit in _max_profit'

    SET_PROFIT_DICT = 'btc profit has reached the min_profit. min_profit={}, profit_dict={}'


class SenderMessage(object):
    pass


class ServerMessage(object):
    pass


class TradingMessage(object):
    class Info(object):
        pass

    class Debug(object):
        TRADING_RESULT = 'trading_result=[{}]'
        FAIL_TO_TRADING = 'Fail trading, trading_result=[{}]'
        TRADING_INFORMATION = 'trading_information=[{}]'
        INFORMATION_NOT_FOUND = 'information not found'

    def debugger(self):
        pass


class WithdrawalMessage(object):
    pass


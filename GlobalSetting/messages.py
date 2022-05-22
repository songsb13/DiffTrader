"""
Logging Messages
"""

"""
    Logs 정책
    debug들은 내부에서 다 처리하고, 윗단 값들 (trade_thread.py) 등은 debug 최소화.
    대신 info들 노출시켜 주는 것에 중점을 둬야함.
"""

import inspect


class CommonMessage(object):
    """
        Info message, 모든 프로세스에서 사용함.
    """

    START = '프로그램을 시작합니다.'
    FATAL = '프로그램 에러가 발생했습니다.'

    # for check entering & Exit function
    ENTRANCE = 'Function Entrance'
    EXIT = 'Function Exit.'

    @staticmethod
    def entrance_with_parameter(fn, value):
        sig = inspect.signature(fn)
        param_dict = dict(sig.bind(*value).arguments)
        return f'Function Entrance, {param_dict}'


class SetterMessage(object):
    START = 'start setter process, user={}, exchange_str={}'


class MonitoringMessage(object):
    SET_MONITORING = 'Start monitoring process, Primary={}, Secondary={}, User={}'
    RUNNING = 'running monitoring process, primary={}, secondary={}, user={}'
    GET_ERROR_MESSAGE_IN_COMPARE = 'get error message in _compare_orderbook. error_message={}'
    BALANCE_NOT_FOUND = '{}, has not {} in currency balance.'
    EXPECTED_PROFIT = "expected profit is not enough to reach setting's profit. coin:{}, {} < {}"
    TRADABLE_INFO = "tradable={}, coin_amount={}, sell_coin_amonut={}, btc_profit={}, real_difference={}"

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


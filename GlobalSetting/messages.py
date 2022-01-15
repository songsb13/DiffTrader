"""
Logging Messages
"""

import logging
import os
import sys
import datetime

"""
    Logs 정책
    debug들은 내부에서 다 처리하고, 윗단 값들 (trade_thread.py) 등은 debug 최소화.
    대신 info들 노출시켜 주는 것에 중점을 둬야함.
"""


class GlobalMessage(object):
    ENTRANCE = 'parameters={data}'
    FATAL = 'FATAL'


class MonitoringMessage(object):
    pass


class SenderMessage(object):
    pass


class ServerMessage(object):
    pass


class SetterMessage(object):
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


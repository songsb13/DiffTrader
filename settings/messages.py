"""
Logging 관련 message 집합
"""

import logging
import os, sys
import datetime


# todo log 방식에 대한 저장 명시 필요
# JSON, pickle 등으로 저장?
"""
    Logs 정책
    debug들은 내부에서 다 처리하고, 윗단 값들 (trade_thread.py) 등은 debug 최소화.
    대신 info들 노출시켜 주는 것에 중점을 둬야함.
"""


class Logs(logging.Logger):
    def __init__(self, signal):
        super(Logs, self).__init__()
        self.signal = signal

    # todo debug level에 대한 정의도 필요함
    def send(self, message):
        self.signal.emit(logging.INFO, message)

    EXCEPT_ERROR = (logging.ERROR, '프로그램에 예기치 못한 문제가 발생하였습니다. 로그를 개발자에게 즉시 보내주세요.')


class Messages(object):

    class Init(object):
        """
            프로그램 시작 이후부터 event가 loop돌면서 값을 찾기 전까지 message 집합
        """
        START = '자동 차익매매 감지 시작'
        MIN_PROFIT = '최소 %: {min_profit}%'
        MIN_BTC = '최소 BTC: {min_btc}'
        WRONG_INPUT = '잘못된 값이 설정되어 있습니다. 설정 값을 확인해 주세요.'
        AUTO = '자동 출금 여부: {auto_withdrawal}'

        GET_WITHDRAWAL_INFO = '출금 정보를 가져오는 중입니다.'
        FAIL_WITHDRAWAL_INFO = '출금 정보를 가져오지 못했습니다. 정보 확인 후 다시 시작해 주세요.'
        SUCCESS_WITHDRAWAL_INFO = '출금 정보를 가져왔습니다.'


    class Trade(object):
        NO_AVAILABLE = '거래 가능한 코인이 없습니다. 잔고를 확인해 주세요.'
        NO_BALANCE = 'BTC 잔고가 없습니다. 잔고를 확인해 주세요.'
        NO_PROFIT = '만족하는 조건 값을 찾지 못했습니다. 조건을 재검색 합니다.'

        FAIL = '거래에 실패했습니다. 처음부터 다시 시도합니다.'
        SUCCESS = '차익 거래에 성공했습니다.'


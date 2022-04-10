

import configparser
import redis
import os
import sys


DEBUG = True if 'pydevd' in sys.modules else False
DEBUG_ORDER_ID = 'DEBUG-TEST-ID'

TEST_USER = 'gimo@naver.com'

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'config.cfg'))

REDIS_SERVER = redis.StrictRedis(host='localhost', port=6379, db=0)
AGREE_WORDS = ['Y', 'YES', 'TRUE', 'T']
FUNCTIONS = ['Setter', 'Sender', 'Monitoring', 'Trading', 'Withdrawal']


class PicklePath(object):
    WITHDRAWAL = './withdrawal.pickle'


class TraderConsts(object):
    # Selling the BTC from primary, Selling the ALT from secondary
    PRIMARY_TO_SECONDARY = 'primary_to_secondary'

    # Selling the ALT from primary, Selling the BTc from secondary
    SECONDARY_TO_PRIMARY = 'secondary_to_primary'

    TAG_COINS = ['XRP', 'XMR']
    ABLE_MARKETS = ['BTC']

    # set default refresh time
    DEFAULT_REFRESH_TIME = 3600

    # Exchange list of available trading in SAI programs.
    AVAILABLE_EXCHANGES = ['Binance', 'Bithumb', 'Upbit']


class SaiUrls(object):
    BASE = 'https://www.saiblockchain.com'

    TRADING = '/api/v1/information/trading'
    WITHDRAWAL = '/api/v1/information/withdrawal'

    EXPECTED_PROFIT = '/api/v1/information/expected-profit'
    REAL_PROFIT = '/api/v1/information/real-profit'

    USER_DATA = '/api/v1/information/user-data'


class MethodType(object):
    POST = 'POST'
    GET = 'GET'
    PUT = 'PUT'
    DELETE = 'DELETE'


class RedisKey(object):
    UserInformation = 'user_information'
    TradingInformation = 'trading_information'
    ProfitInformation = 'profit_information'
    SendInformation = 'send_information'


class QueuePriority(object):
    LOCKALBE = {
        'Setter': 3,
        'Monitoring': 4,
        'Trading': 1,
        'Withdrawal': 2
    }

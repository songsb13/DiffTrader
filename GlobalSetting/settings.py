import configparser
import redis
import os

TAG_COINS = ['XRP', 'XMR']

# Selling the BTC from primary, Selling the ALT from secondary
PRIMARY_TO_SECONDARY = 'primary_to_secondary'

# Selling the ALT from primary, Selling the BTc from secondary
SECONDARY_TO_PRIMARY = 'secondary_to_primary'

# Exchange list of available trading in SAI programs.
AVAILABLE_EXCHANGES = ['Binance', 'Bithumb', 'Upbit']

# set default refresh time
DEFAULT_REFRESH_TIME = 3600

TEST_USER = 'gimo@naver.com'

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'config.cfg'))

REDIS_SERVER = redis.StrictRedis(host='localhost', port=6379, db=0)


class SaiUrls(object):
    BASE = 'https://www.saiblockchain.com'

    TRADING = '/api/v1/information/trading'
    WITHDRAW = '/api/v1/information/withdraw'

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

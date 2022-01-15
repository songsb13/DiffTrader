TAG_COINS = ['XRP', 'XMR']

SAI_URL = 'http://www.saiblockchain.com/api/pft_data'
PROFIT_SAI_URL = 'http://saiblockchain.com/api/expected_profit'

SAVE_DATA_URL = 'http://songsb13.cafe24.com:8081/save_data'
LOAD_DATA_URL = 'http://songsb13.cafe24.com:8081/get_data'
# Selling the BTC from primary, Selling the ALT from secondary
PRIMARY_TO_SECONDARY = 'primary_to_secondary'

# Selling the ALT from primary, Selling the BTc from secondary
SECONDARY_TO_PRIMARY = 'secondary_to_primary'

# Exchange list of available trading in SAI programs.
AVAILABLE_EXCHANGES = ['Binance', 'Bithumb', 'Upbit']

ENABLE_SETTING = '설정'
UNABLE_SETTING = '미설정'

# set default refresh time
DEFAULT_REFRESH_TIME = 3600


class SaiUrls(object):
    BASE = 'https://www.saiblockchain.com'

    class Information(object):
        TRADING = '/api/v1/information/trading'
        WITHDRAW = '/api/v1/information/withdraw'


class MethodType(object):
    POST = 'POST'
    GET = 'GET'
    PUT = 'PUT'
    DELETE = 'DELETE'


class RedisKey(object):
    UserInformation = 'user_information'
    TradingInformation = 'trading_information'
    ProfitInformation = 'profit_information'

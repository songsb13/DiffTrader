import configparser
import redis
import os
import sys
import datetime
import copy


DEBUG = True if "pydevd" in sys.modules else False
DEBUG_ORDER_ID = "DEBUG-TEST-ID"

TEST_USER = "gimo@naver.com"

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), "config.cfg"))

REDIS_SERVER = redis.StrictRedis(host="localhost", port=6379, db=0)
AGREE_WORDS = ["Y", "YES", "TRUE", "T"]

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICKLE_WITHDRAW = "./withdrawal.pickle"


BASE_LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "simple": {"format": "[%(name)s][%(message)s]"},
        "complex": {
            "format": "[%(asctime)s][%(levelname)s][%(filename)s][%(funcName)s][%(message)s]"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "DEBUG",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"parent": {"level": "INFO"}, "parent.child": {"level": "DEBUG"}},
}


class TraderConsts(object):
    # Selling the BTC from primary, Selling the ALT from secondary
    PRIMARY_TO_SECONDARY = "primary_to_secondary"

    # Selling the ALT from primary, Selling the BTc from secondary
    SECONDARY_TO_PRIMARY = "secondary_to_primary"

    TAG_COINS = ["XRP", "XMR"]
    ABLE_MARKETS = ["BTC"]

    # set default refresh time
    DEFAULT_REFRESH_TIME = 3600


class SaiUrls(object):
    BASE = "https://www.saiblockchain.com"

    TRADING = "/api/v1/information/trading"
    WITHDRAWAL = "/api/v1/information/withdrawal"

    EXPECTED_PROFIT = "/api/v1/information/expected-profit"
    REAL_PROFIT = "/api/v1/information/real-profit"

    USER_DATA = "/api/v1/information/user-data"


class MethodType(object):
    POST = "POST"
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"


class RedisKey(object):
    UserInformation = "user_information"
    TradingInformation = "trading_information"
    ProfitInformation = "profit_information"
    SendInformation = "send_information"

    ApiKey = {
            "upbit": {"publish": "publish", "subscribe": "subscribe"},
            "binance": {"publish": "publish", "subscribe": "subscribe"}
    }


class APIPriority(object):
    EXECUTE = 0
    SEARCH = 1
    LENGTH = len([EXECUTE, SEARCH])


class SetLogger(object):
    @staticmethod
    def get_config_base_process(process_name):
        try:
            now = datetime.datetime.now()
            now_date, now_hour = str(now.date()), now.strftime("%Hh%Mm%Ss")

            log_path = os.path.join(ROOT_DIR, "Logs")
            SetLogger.create_dir(log_path)

            log_process_path = os.path.join(log_path, process_name)
            SetLogger.create_dir(log_process_path)

            log_date_path = os.path.join(log_process_path, now_date)
            SetLogger.create_dir(log_date_path)

            copied_base_config = copy.deepcopy(BASE_LOGGING_CONFIG)

            copied_base_config["handlers"][process_name] = {
                "class": "logging.FileHandler",
                "filename": os.path.join(log_date_path, f"{now_hour}.log"),
                "formatter": "complex",
                "level": "DEBUG",
            }
            copied_base_config["root"]["handlers"].append(process_name)

            return copied_base_config

        except Exception as ex:
            print(ex)

    @staticmethod
    def create_dir(path):
        if not os.path.isdir(path):
            os.mkdir(path)

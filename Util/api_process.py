from DiffTrader.GlobalSetting.objects import BaseAPIProcess
from DiffTrader.GlobalSetting.settings import RedisKey


class UpbitAPIProcess(BaseAPIProcess):
    api_redis_key = RedisKey.UpbitAPISubRedisKey

    def __init__(self, exchange_str):
        super(UpbitAPIProcess, self).__init__(exchange_str)


class BinanceAPIProcess(BaseAPIProcess):
    api_redis_key = RedisKey.BinanceAPISubRedisKey

    def __init__(self,  exchange_str):
        super(BinanceAPIProcess, self).__init__(exchange_str)

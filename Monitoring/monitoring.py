from Exchanges.settings import *
from DiffTrader.Util.utils import get_exchanges, FunctionExecutor, set_redis, get_redis
from DiffTrader.GlobalSetting.settings import *
from Util.pyinstaller_patch import *


class Monitoring(object):
    def monitoring(self):
        latest_user_information = None
        while True:
            user_information = get_redis(RedisKey.UserInformation)
            if not user_information and not latest_user_information:
                continue

            latest_user_information = user_information



from Util.pyinstaller_patch import *
from datetime import datetime


def get_expected_profit_by_server():
    profit_path = 'http://saiblockchain.com/api/expected_profit'
    now_date = time.time()
    yesterday = now_date - 24 * 60 * 60

    rq = requests.get(profit_path, json={'from': yesterday, 'to': now_date})
    result = rq.json()
    if result:
        for date_ in result:
            profit_date = datetime.fromtimestamp(date_[-1]).strftime(
                '%Y{} %m{} %d{} %H{} %M{}').format('년', '월', '일', '시', '분')
            date_[-1] = profit_date

        return date_



from DiffTrader.apps.threads import time, datetime
from DiffTrader.apps.threads import SAI_URL, PROFIT_SAI_URL

import requests


def get_expected_profit_by_server():
    """
        Get expected_profit from saiblockchain api server.
    """
    now_date = time.time()
    yesterday = now_date - 24 * 60 * 60

    rq = requests.get(PROFIT_SAI_URL, json={'from': yesterday, 'to': now_date})
    result = rq.json()
    if result:
        for date_ in result:
            profit_date = datetime.fromtimestamp(date_[-1]).strftime(
                '%Y{} %m{} %d{} %H{} %M{}').format('년', '월', '일', '시', '분')
            date_[-1] = profit_date

        return result


def send_expected_profit(profit_object):
    """
    """
    res = requests.post(SAI_URL, data=profit_object.information)

    return True if res.status_code == 200 else False

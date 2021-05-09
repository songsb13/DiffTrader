from DiffTrader.trading.threads import time, datetime
from DiffTrader.trading.settings import SAI_URL, PROFIT_SAI_URL, SAVE_DATA_URL, LOAD_DATA_URL

import requests
import copy


def get_expected_profit_by_server(user_id):
    """
        Get expected_profit from saiblockchain api server.
    """
    now_date = time.time()
    yesterday = now_date - 24 * 60 * 60

    rq = requests.get(PROFIT_SAI_URL, json={'user_id': user_id, 'from': yesterday, 'to': now_date})
    result = rq.json()
    if result:
        copied_result = copy.deepcopy(result)
        for date_ in enumerate(copied_result):
            profit_date = datetime.fromtimestamp(date_[-1]).strftime(
                '%Y{} %m{} %d{} %H{} %M{}').format('년', '월', '일', '시', '분')
            date_[-1] = profit_date

        return result


def send_expected_profit(profit_object):
    """
    """
    res = requests.post(SAI_URL, data=profit_object.information)

    return True if res.status_code == 200 else False


def save_total_data_to_database(id_key, min_profit_percent, min_profit_btc, is_withdraw):
    dic = dict()
    row = [id_key, min_profit_percent, min_profit_btc, is_withdraw]
    for num, each in enumerate(['id_key', 'min_profit_percent', 'min_profit_btc', 'is_withdraw']):
        dic.setdefault(each, row[num])

    rq = requests.get(SAVE_DATA_URL, json=dic)

    result = rq.json()

    return True if result.get('success') else False


def load_total_data_to_database(id_key):
    try:
        dic = dict(id_key=id_key)
        rq = requests.get(LOAD_DATA_URL, json=dic)

        raw_result = rq.json()
        result = raw_result[0]

        min_profit_percent = result.get('min_profit_percent')
        min_profit_btc = result.get('min_profit_btc')
        is_withdraw = True if result.get('is_withdraw') else False
        return dict(
            min_profit_percent=min_profit_percent,
            min_profit_btc=min_profit_btc,
            auto_withdrawal=is_withdraw
        )
    except:
        return dict()

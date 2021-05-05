import logging
import sys

from DiffTrader.server.models import ProfitSettingTable
from flask import Flask
from flask import request
from flask_mysqldb import MySQL
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

f_hdlr = logging.FileHandler('logger.log')
s_hdlr = logging.StreamHandler()

logger.addHandler(f_hdlr)
logger.addHandler(s_hdlr)

app = Flask(__name__)
if 'pydevd' in sys.modules:
    app.config['MYSQL_USER'] = 'localhost'

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'

mysql = MySQL(app)


@app.route('/save_data', methods=['GET'])
def data_truck():
    # todo server 개선, 가독성 개선, 접근 url 변경, execute 방식 점검 필요함.
    try:
        data = request.json
        
        cursor = mysql.connection.cursor()

        # table은 미리 만들어져 있는 상태?
        # query = ProfitSettingTable.create_min_profit_data_table()
        # cursor.execute(query)

        exists_query = ProfitSettingTable.has_already_exists_profit_setting_table()

        cursor.execute(exists_query, (data['user_id']))
        if cursor.fetchone():
            data_query = ProfitSettingTable.update_profit_setting_table()
        else:
            data_query = ProfitSettingTable.insert_profit_setting_table()
        data_list = (data['user_id'], data['min_profit_percent'], data['min_profit_btc'], data['auto_withdrawal'])
        cursor.execute(data_query, data_list)
        mysql.connection.commit()

        result = dict(success=True)
    except Exception as e:
        result = dict(success=False, message=e)

    return json.dumpss(result)


@app.route('/get_data', methods=['GET'])
def data_loader():
    data = request.json

    cursor = mysql.connection.cursor()

    cursor.execute("USE profit_settings")

    load_qry = '''
    SELECT * FROM settings where id_key = %s
    '''

    cursor.execute(load_qry, (data['id_key'],))
    _list = []
    for data in cursor.fetchall():
        _dic = {}
        for data_num, colsub in enumerate(cursor.description):
            _dic[colsub[0]] = data[data_num]
        _list.append(_dic)
    return json.dumps(_list)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8081, threaded=True)

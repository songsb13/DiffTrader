import logging
import sys
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
    try:
        data = request.json
        
        cursor = mysql.connection.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS profit_settings")

        cursor.execute("USE profit_settings")

        tb_query = '''
            CREATE TABLE IF NOT EXISTS settings(
            id_key INT PRIMARY KEY ,
            min_pft_per float NOT NULL,
            min_pft_btc float NOT NULL,
            is_withdraw boolean NOT NULL)
        '''
        cursor.execute(tb_query)

        cursor.execute('SELECT * FROM settings WHERE id_key = %s',(data['id_key'],))

        if cursor.fetchone():
            qry = '''
            UPDATE settings set min_pft_per = %s, min_pft_btc = %s, is_withdraw = %s WHERE id_key = %s
            '''
        else:
            qry = '''
            INSERT INTO settings(min_pft_per, min_pft_btc, is_withdraw, id_key)
            VALUES(%s, %s, %s, %s)
            '''

        #        for _i in ('min_pft_per', 'min_pft_btc', 'is_withdrwal'):

        data_list = (data['min_pft_per'], data['min_pft_btc'], data['is_withdraw'], data['id_key'])
        cursor.execute(qry, data_list)
        mysql.connection.commit()
        suc = {'success': True}
    except Exception as e:
        print(e)
        suc = {'success': False, 'msg': e}

    return json.dumps(suc)


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

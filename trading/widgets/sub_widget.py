from . import *
from DiffTrader.trading.apis import save_total_data_to_database, load_total_data_to_database
from DiffTrader.trading.messages import QMessageBoxMessage as Qmsg

import requests


class MinProfitWidget(QtWidgets.QWidget, ProgramWidgets.PROFIT_SETTING_WIDGET):
    def __init__(self, id_key):
        super().__init__()
        self.setupUi(self)
        self.id_key = id_key
        self.save_button.clicked.connect(self.save_data_to_db)

        load_total_data_to_database(id_key)

    def save_data_to_db(self):
        id_key = self.id_key
        try:
            min_profit_percent = float(self.min_pft_per.text())
            min_profit_btc = float(self.min_pft_btc.text())
            is_right = True
        except:
            QtWidgets.QMessageBox.about(self, 'Messsage', '최소수익에는 숫자가 들어가야합니다.')
            is_right = False

        if is_right:
            withdraw_setting_text = self.withdraw_setting.currentText()

            if withdraw_setting_text == '설정':
                is_withdraw = True
            else:
                is_withdraw = False

            success = save_total_data_to_database(self.id_key, min_profit_percent, min_profit_btc, is_withdraw)

            log = (Qmsg.Title.SAVE_RESULT, Qmsg.CONTENT.SAVE_SUCCESS if success else Qmsg.CONTENT.SAVE_FAIL)
            debugger.debug(log)
            QtWidgets.QMessageBox.about(self, *log)

        _rq = requests.get('http://songsb13.cafe24.com:8081/get_data', json={'id_key': self.id_key}).json()
        for data in _rq:
            self.min_pft_per.setValue(data['min_pft_per'])
            self.min_pft_btc.setValue(data['min_pft_btc'])

            index = 1 if bool(data['is_withdraw']) else 0
            self.withdraw_setting.setCurrentIndex(index)


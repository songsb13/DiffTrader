from Util.pyinstaller_patch import *
from PyQt5 import QtWidgets
import requests

from settings.widget_paths import ProgramSettingWidgets as widgets


class MinProfitWidget(QtWidgets.QWidget, widgets.PROFIT_SETTING_WIDGET):
    def __init__(self, id_key):
        super().__init__()
        self.setupUi(self)
        self.id_key = id_key
        self.load_data_to_db()
        self.save_button.clicked.connect(self.save_data_to_db)

    def save_data_to_db(self):
        id_key = self.id_key
        try:
            min_pft_per = float(self.min_pft_per.text())
            min_pft_btc = float(self.min_pft_btc.text())
            is_right = True
        except:
            QtWidgets.QMessageBox.about(None, 'Messsage', '최소수익에는 숫자가 들어가야합니다.')
            is_right = False

        if is_right:
            withdraw_setting_text = self.withdraw_setting.currentText()

            if withdraw_setting_text == '설정':
                is_withdraw = True
            else:
                is_withdraw = False

            data_dic = {}
            for _i in ('id_key', 'min_pft_per', 'min_pft_btc', 'is_withdraw'):
                data_dic[_i] = locals()[_i]
            _rq = requests.get('http://songsb13.cafe24.com:8081/save_data', json=data_dic).json()

            if _rq['success']:
                QtWidgets.QMessageBox.about(None, 'Success', '저장에 성공했습니다.')
            else:
                QtWidgets.QMessageBox.about(None, 'Fail', '저장에 실패했습니다.')

    def load_data_to_db(self):
        _rq = requests.get('http://songsb13.cafe24.com:8081/get_data', json={'id_key': self.id_key}).json()

        for data in _rq:
            self.min_pft_per.setValue(data['min_pft_per'])
            self.min_pft_btc.setValue(data['min_pft_btc'])

            if bool(data['is_withdraw']):
                index = 1
            else:
                index = 0
            self.withdraw_setting.setCurrentIndex(index)

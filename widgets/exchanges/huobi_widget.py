from Util.pyinstaller_patch import *
from PyQt5 import QtWidgets, uic
from settings_encryptor import SettingEncryptKeyDialog

widget_path = os.path.join(sys._MEIPASS, 'ui/HuobiWidget.ui')

widget = uic.loadUiType(widget_path)[0]


class HuobiWidget(QtWidgets.QWidget, widget):
    def __init__(self, data):
        super().__init__()
        self.setupUi(self)
        self.dialog = SettingEncryptKeyDialog()
        self.dialog.btn.accepted.connect(self.save)
        self.checkBox.clicked.connect(self.show_secret)
        self.pushButton.clicked.connect(self.dialog.show)

        self.saved = False

        if data and 'huobi' in data.keys():
            self.key.setText(data['huobi']['key'])
            self.secret.setText(data['huobi']['secret'])
            if 'form' in self.__dict__:
                self.form.setCurrentIndex(data['huobi']['form'])
                self.USDT_form_value.setValue(data['huobi']['usdt_form_value'])
                self.BTC_form_value.setValue(data['huobi']['btc_form_value'])
                self.ETH_form_value.setValue(data['huobi']['eth_form_value'])
                self.HT_form_value.setValue(data['huobi']['ht_form_value'])
            self.saved = True

    def save(self):
        if 'form' in self.__dict__:
            self.dialog.save('huobi', key=self.key.text(), secret=self.secret.text(),
                             form=self.form.currentIndex(),
                             usdt_form_value=self.USDT_form_value.value(),
                             btc_form_value=self.BTC_form_value.value(),
                             eth_form_value=self.ETH_form_value.value(),
                             ht_form_value=self.HT_form_value.value())
        else:
            self.dialog.save('huobi', key=self.key.text(), secret=self.secret.text())
        self.saved = True

    def show_secret(self):
        if self.checkBox.isChecked():
            self.secret.setEchoMode(0)
        else:
            self.secret.setEchoMode(2)

    def is_set(self):
        if self.key.text() and self.secret.text():
            return True
        else:
            return False

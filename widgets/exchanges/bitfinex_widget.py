from pyinstaller_patch import *
from PyQt5 import QtWidgets, uic
from settings_encryptor import SettingEncryptKeyDialog

WIDGET_PATH = os.path.join(sys._MEIPASS, 'ui/BitfinexWidget.ui')

widget = uic.loadUiType(WIDGET_PATH)[0]


class BitfinexWidget(QtWidgets.QWidget, widget):
    def __init__(self, data):
        super().__init__()
        self.setupUi(self)
        self.dialog = SettingEncryptKeyDialog()
        self.dialog.btn.accepted.connect(self.save)
        self.checkBox.clicked.connect(self.show_secret)
        self.pushButton.clicked.connect(self.dialog.show)

        self.saved = False

        if data and 'bitfinex' in data.keys():
            self.key.setText(data['bitfinex']['key'])
            self.secret.setText(data['bitfinex']['secret'])
            if 'form' in self.__dict__:
                self.form.setCurrentIndex(data['bitfinex']['form'])
                self.USD_form_value.setValue(data['bitfinex']['usd_form_value'])
                self.EUR_form_value.setValue(data['bitfinex']['eur_form_value'])
                self.GBP_form_value.setValue(data['bitfinex']['gbp_form_value'])
                self.JYP_form_value.setValue(data['bitfinex']['jyp_form_value'])
                self.BTC_form_value.setValue(data['bitfinex']['btc_form_value'])
                self.ETH_form_value.setValue(data['bitfinex']['eth_form_value'])
                self.EOS_form_value.setValue(data['bitfinex']['eos_form_value'])
                self.XLM_form_value.setValue(data['bitfinex']['xlm_form_value'])
            self.saved = True

    def save(self):
        if 'form' in self.__dict__:
            self.dialog.save('bitfinex', key=self.key.text(), secret=self.secret.text(),
                             form=self.form.currentIndex(),
                             usd_form_value=self.USD_form_value.value(),
                             eur_form_value=self.EUR_form_value.value(),
                             gbp_form_value=self.GBP_form_value.value(),
                             jyp_form_value=self.JYP_form_value.value(),
                             btc_form_value=self.BTC_form_value.value(),
                             eth_form_value=self.ETH_form_value.value(),
                             eos_form_value=self.EOS_form_value.value(),
                             xlm_form_value=self.XLM_form_value.value()
                             )
        else:
            self.dialog.save('bitfinex', key=self.key.text(), secret=self.secret.text())
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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    gui = BitfinexWidget()
    gui.show()
    sys.exit(app.exec_())

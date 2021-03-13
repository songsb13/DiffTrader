from pyinstaller_patch import *
from widgets.base_widget import BaseWidgets
from settings.widget_paths import ExchangeWidgets as widgets


class BinanceWidget(BaseWidgets, widgets.BINANCE_WIDGET):
    def __init__(self, data):
        super().__init__()
        self.setupUi(self)

        if data and 'binance' in data.keys():
            self.key.setText(data['binance']['key'])
            self.secret.setText(data['binance']['secret'])
            if 'form' in self.__dict__:
                self.form.setCurrentIndex(data['binance']['form'])
                self.BNB_form_value.setValue(data['binance']['bnb_form_value'])
                self.BTC_form_value.setValue(data['binance']['btc_form_value'])
                self.ETH_form_value.setValue(data['binance']['eth_form_value'])
                self.XRP_form_value.setValue(data['binance']['xrp_form_value'])
                self.USDT_form_value.setValue(data['binance']['usdt_form_value'])
                self.USDC_form_value.setValue(data['binance']['usdc_form_value'])
                self.TUSD_form_value.setValue(data['binance']['tusd_form_value'])
                self.PAX_form_value.setValue(data['binance']['pax_form_value'])
            self.saved = True

    def save(self):
        if 'form' in self.__dict__:
            self.dialog.save('binance', key=self.key.text(), secret=self.secret.text(),
                             form=self.form.currentIndex(),
                             bnb_form_value=self.BNB_form_value.value(),
                             btc_form_value=self.BTC_form_value.value(),
                             eth_form_value=self.ETH_form_value.value(),
                             xrp_form_value=self.XRP_form_value.value(),
                             usdt_form_value=self.USDT_form_value.value(),
                             usdc_form_value=self.USDC_form_value.value(),
                             tusd_form_value=self.TUSD_form_value.value(),
                             pax_form_value=self.PAX_form_value.value())
        else:
            self.dialog.save('binance', key=self.key.text(), secret=self.secret.text())
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

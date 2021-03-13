from pyinstaller_patch import *
from widgets.base_widget import BaseWidgets
from settings.widget_paths import ExchangeWidgets as widgets


class UpbitWidget(BaseWidgets, widgets.UPBIT_WIDGET):
    def __init__(self, data):
        super().__init__()
        self.setupUi(self)

        if data and 'upbit' in data.keys():
            self.id.setText(data['upbit']['id'])
            self.pw.setText(data['upbit']['pw'])
            self.tkey.setText(data['upbit']['tkey'])
            self.tchatid.setText(data['upbit']['tchatid'])
            if 'form' in self.__dict__:
                self.form.setCurrentIndex(data['upbit']['form'])
                self.KRW_form_value.setValue(data['upbit']['krw_form_value'])
                self.BTC_form_value.setValue(data['upbit']['btc_form_value'])
                self.ETH_form_value.setValue(data['upbit']['eth_form_value'])
                self.USDT_form_value.setValue(data['upbit']['usdt_form_value'])
            self.saved = True

    def save(self):
        if 'form' in self.__dict__:
            self.dialog.save('upbit', id=self.id.text(), pw=self.pw.text(), tkey=self.tkey.text(),
                             tchatid=self.tchatid.text(),
                             form=self.form.currentIndex(),
                             krw_form_value=self.KRW_form_value.value(),
                             btc_form_value=self.BTC_form_value.value(),
                             eth_form_value=self.ETH_form_value.value(),
                             usdt_form_value=self.USDT_form_value.value())
        else:
            self.dialog.save('upbit', id=self.id.text(), pw=self.pw.text(), tkey=self.tkey.text(),
                             tchatid=self.tchatid.text())
        self.saved = True

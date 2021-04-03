class ExchangeBaseWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ExchangeBaseWidget, self).__init__()
        self.dialog = SettingEncryptKeyDialog()
        self.dialog.btn.accepted.connect(self.save)
        self.showSecretBtn.clicked.connect(self.show_secret)
        self.saveBtn.clicked.connect(self.dialog.show)
        self.saved = False

    def load_key_and_secret(self, exchange_str, data):
        exchange_info = data.get(exchange_str, None)

        if exchange_info:
            self.key.setText(exchange_info['key'])
            self.secret.setText(exchange_info['secret'])

            self.saved = True

    def save(self):
        self.dialog.save(key=self.key.text(), secret=self.secret.text())

        self.saved = True

    def show_secret(self):
        if self.showSecretBox.isChecked():
            self.secret.setEchoMode(0)
        else:
            self.secret.setEchoMode(2)

    def is_set(self):
        if self.key.text() and self.secret.text():
            return True
        else:
            return False


class ExchangeSelectorWidget(QtWidgets.QWidget, widgets.EXCHANGE_SELECTOR_WIDGET):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class BithumbWidget(ExchangeBaseWidget, widgets.BITHUMB_WIDGET):
    def __init__(self, data):
        super().__init__()
        self.setupUi(self)

        if data and 'bithumb' in data.keys():
            self.key.setText(data['bithumb']['key'])
            self.secret.setText(data['bithumb']['secret'])
            if 'form' in self.__dict__:
                self.form.setCurrentIndex(data['bithumb']['form'])
                self.KRW_form_value.setValue(data['bithumb']['krw_form_value'])
            self.saved = True

    def save(self):
        if 'form' in self.__dict__:
            self.dialog.save('bithumb', key=self.key.text(),
                             secret=self.secret.text(),
                             form=self.form.currentIndex(),
                             krw_form_value=self.KRW_form_value.value())
        else:
            self.dialog.save('bithumb', key=self.key.text(),
                             secret=self.secret.text())
        self.saved = True


class BinanceWidget(ExchangeBaseWidget, widgets.BINANCE_WIDGET):
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


class UpbitWidget(ExchangeBaseWidget, widgets.UPBIT_WIDGET):
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


# class BitfinexWidget(QtWidgets.QWidget, widget):
#     def __init__(self, data):
#         super().__init__()
#         self.setupUi(self)
#         self.dialog = SettingEncryptKeyDialog()
#         self.dialog.btn.accepted.connect(self.save)
#         self.checkBox.clicked.connect(self.show_secret)
#         self.pushButton.clicked.connect(self.dialog.show)
#
#         self.saved = False
#
#         if data and 'bitfinex' in data.keys():
#             self.key.setText(data['bitfinex']['key'])
#             self.secret.setText(data['bitfinex']['secret'])
#             if 'form' in self.__dict__:
#                 self.form.setCurrentIndex(data['bitfinex']['form'])
#                 self.USD_form_value.setValue(data['bitfinex']['usd_form_value'])
#                 self.EUR_form_value.setValue(data['bitfinex']['eur_form_value'])
#                 self.GBP_form_value.setValue(data['bitfinex']['gbp_form_value'])
#                 self.JYP_form_value.setValue(data['bitfinex']['jyp_form_value'])
#                 self.BTC_form_value.setValue(data['bitfinex']['btc_form_value'])
#                 self.ETH_form_value.setValue(data['bitfinex']['eth_form_value'])
#                 self.EOS_form_value.setValue(data['bitfinex']['eos_form_value'])
#                 self.XLM_form_value.setValue(data['bitfinex']['xlm_form_value'])
#             self.saved = True
#
#     def save(self):
#         if 'form' in self.__dict__:
#             self.dialog.save('bitfinex', key=self.key.text(), secret=self.secret.text(),
#                              form=self.form.currentIndex(),
#                              usd_form_value=self.USD_form_value.value(),
#                              eur_form_value=self.EUR_form_value.value(),
#                              gbp_form_value=self.GBP_form_value.value(),
#                              jyp_form_value=self.JYP_form_value.value(),
#                              btc_form_value=self.BTC_form_value.value(),
#                              eth_form_value=self.ETH_form_value.value(),
#                              eos_form_value=self.EOS_form_value.value(),
#                              xlm_form_value=self.XLM_form_value.value()
#                              )
#         else:
#             self.dialog.save('bitfinex', key=self.key.text(), secret=self.secret.text())
#         self.saved = True
#
#     def show_secret(self):
#         if self.checkBox.isChecked():
#             self.secret.setEchoMode(0)
#         else:
#             self.secret.setEchoMode(2)
#
#     def is_set(self):
#         if self.key.text() and self.secret.text():
#             return True
#         else:
#             return False

# class HuobiWidget(QtWidgets.QWidget, widget):
#     def __init__(self, data):
#         super().__init__()
#         self.setupUi(self)
#         self.dialog = SettingEncryptKeyDialog()
#         self.dialog.btn.accepted.connect(self.save)
#         self.checkBox.clicked.connect(self.show_secret)
#         self.pushButton.clicked.connect(self.dialog.show)
#
#         self.saved = False
#
#         if data and 'huobi' in data.keys():
#             self.key.setText(data['huobi']['key'])
#             self.secret.setText(data['huobi']['secret'])
#             if 'form' in self.__dict__:
#                 self.form.setCurrentIndex(data['huobi']['form'])
#                 self.USDT_form_value.setValue(data['huobi']['usdt_form_value'])
#                 self.BTC_form_value.setValue(data['huobi']['btc_form_value'])
#                 self.ETH_form_value.setValue(data['huobi']['eth_form_value'])
#                 self.HT_form_value.setValue(data['huobi']['ht_form_value'])
#             self.saved = True
#
#     def save(self):
#         if 'form' in self.__dict__:
#             self.dialog.save('huobi', key=self.key.text(), secret=self.secret.text(),
#                              form=self.form.currentIndex(),
#                              usdt_form_value=self.USDT_form_value.value(),
#                              btc_form_value=self.BTC_form_value.value(),
#                              eth_form_value=self.ETH_form_value.value(),
#                              ht_form_value=self.HT_form_value.value())
#         else:
#             self.dialog.save('huobi', key=self.key.text(), secret=self.secret.text())
#         self.saved = True
#
#     def show_secret(self):
#         if self.checkBox.isChecked():
#             self.secret.setEchoMode(0)
#         else:
#             self.secret.setEchoMode(2)
#
#     def is_set(self):
#         if self.key.text() and self.secret.text():
#             return True
#         else:
#             return False

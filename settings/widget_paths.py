import os
import sys
from PyQt5 import uic


class ExchangeWidgets(object):
    UPBIT_WIDGET = uic.loadUiType(os.path.join(sys._MEIPASS, 'ui/exchanges/UpbitWidget.ui'))[0]
    BINANCE_WIDGET = uic.loadUiType(os.path.join(sys._MEIPASS, 'ui/exchanges/BinanceWidget.ui'))[0]
    BITHUMB_WIDGET = uic.loadUiType(os.path.join(sys._MEIPASS, 'ui/exchanges/BithumbWidget.ui'))[0]


class DialogWidgets(object):
    KEY_DIALOG_WIDGET = uic.loadUiType(os.path.join(sys._MEIPASS, 'ui/SettingEncryptKeyDialog.ui'))[0]
    CONFIRM_DIALOG_WIDGET = uic.loadUiType(os.path.join(sys._MEIPASS, 'ui/DifferentKeyInputDialog.ui'))[0]


class ProgramSettingWidgets(object):
    PROFIT_SETTING_WIDGET = uic.loadUiType(os.path.join(sys._MEIPASS, 'ui/ProfitSettingWidget.ui'))[0]


class FirstPageWidgets(object):
    EXCHANGE_SELECTOR_WIDGET = uic.loadUiType(os.path.join(sys._MEIPASS, 'ui/ExchangeSelectorWidget.ui'))[0]

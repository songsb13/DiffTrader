import os
import sys

from PyQt5 import uic

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class LoginWidgets(object):
    LOGIN = uic.loadUiType(ROOT_DIR, os.path.join('static/guis/Login.ui')[0])


class ExchangeWidgets(object):
    UPBIT_WIDGET = uic.loadUiType(os.path.join(ROOT_DIR, 'static/guis/exchanges/UpbitWidget.ui'))[0]
    BINANCE_WIDGET = uic.loadUiType(os.path.join(ROOT_DIR, 'static/guis/exchanges/BinanceWidget.ui'))[0]
    BITHUMB_WIDGET = uic.loadUiType(os.path.join(ROOT_DIR, 'static/guis/exchanges/BithumbWidget.ui'))[0]


class DialogWidgets(object):
    KEY_DIALOG_WIDGET = uic.loadUiType(os.path.join(ROOT_DIR, 'static/guis/SettingEncryptKeyDialog.ui'))[0]
    CONFIRM_DIALOG_WIDGET = uic.loadUiType(os.path.join(ROOT_DIR, 'static/guis/DifferentKeyInputDialog.ui'))[0]


class ProgramSettingWidgets(object):
    PROFIT_SETTING_WIDGET = uic.loadUiType(os.path.join(ROOT_DIR, 'static/guis/ProfitSettingWidget.ui'))[0]
    DIFF_TRADER_WIDGET = uic.loadUiType(os.path.join(ROOT_DIR, 'static/guis/main.ui'), from_imports=True, import_from='ui')[0]

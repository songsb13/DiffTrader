from PyQt5 import QtWidgets, uic
import sys
import os

WIDGET_PATH = os.path.join(sys._MEIPASS, 'ui/ExchangeSelectorWidget.ui')

widget = uic.loadUiType(WIDGET_PATH)[0]


class ExchangeSelectorWidget(QtWidgets.QWidget, widget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

from PyQt5 import QtWidgets


from settings.widget_paths import FirstPageWidgets as widgets


class ExchangeSelectorWidget(QtWidgets.QWidget, widgets.EXCHANGE_SELECTOR_WIDGET):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

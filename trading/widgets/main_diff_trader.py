from . import *

from DiffTrader.trading.threads.trade_thread import TradeThread
from DiffTrader.trading.threads.profit_thread import TopProfitThread

from DiffTrader.trading.widgets.dialogs import LoadSettingsDialog
from DiffTrader.trading.widgets.paths import (ProgramSettingWidgets)
from DiffTrader.trading.widgets.exchanges import (BithumbWidget, UpbitWidget,
                                                  BinanceWidget, ExchangeSelectorWidget)
from DiffTrader.trading.widgets.sub_widget import MinProfitWidget
from DiffTrader.trading.models import TradeTableModel


class DiffTraderGUI(QtWidgets.QMainWindow, ProgramSettingWidgets.DIFF_TRADER_WIDGET):
    closed = QtCore.pyqtSignal()

    def __init__(self, _id, email, parent=None):
        """
        """
        super().__init__()

        self._user_id = _id
        self._email = email
        self._parent = parent

        self.setupUi(self)

    def start_trade(self):
        self.startTradeBtn.setEnabled(False)
        self.stop_trade_btn.setEnabled(True)

        primary_widget = self.exchange_widgets.get(self.primary_exchange_str)
        secondary_widget = self.exchange_widgets.get(self.secondary_exchange_str)

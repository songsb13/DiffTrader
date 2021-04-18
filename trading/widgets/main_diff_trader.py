from . import *

from DiffTrader.trading.widgets.paths import (ProgramSettingWidgets)
from DiffTrader.trading.settings import AVAILABLE_EXCHANGES


class DiffTraderGUI(QtWidgets.QMainWindow, ProgramSettingWidgets.DIFF_TRADER_WIDGET):
    closed = QtCore.pyqtSignal()

    def __init__(self, _id, email, parent=None):
        """
        """
        super().__init__()

        self.user_id = _id
        self.email = email
        self.parent = parent

        self.setupUi(self)
        
        # define tab widgets
        self._main_tab_widget = self.MainTab(self)
    
    def closeEvent(self, *args, **kwargs):
        close_program(self._id)
        self.top_profit_thread.exit()
        self.closed.emit()

    class MainTab(object):
        """
            It is a tab to start trading after selecting two widgets.
            Also it is located with profit table, profit top 10 table, log widget.
        """
        def __init__(self, diff_gui):
            """
                Args:
                    diff_gui: diffTraderGUI(object)
            """
            self._diff_gui = diff_gui
            self._user_id = diff_gui.user_id
            self._email = diff_gui.email
            self._parent = diff_gui.parent
            
            # connect buttons
            self._diff_gui.startTradeBtn.clicked.connect(self.start_trade)
            self._diff_gui.stopTradeBtn.clicked.connect(self.stop_trade)

            # exchange select bar settings
            self._diff_gui.primaryExchange.addItems(AVAILABLE_EXCHANGES)
            self._diff_gui.secondaryExchange.addItems(AVAILABLE_EXCHANGES)

            self._diff_gui.primaryExchange.currentIndexChanged.connect(self.same_exchange_checker)
            # self._diff_gui.secondaryExchange.currentIndexChanged.connect(self.same_exchange_checker)

        def same_exchange_checker(self):
            """
                check the exchange is selected twice from primary and secondary.
            """
            if self._diff_gui.primaryExchange.currentText() == self._diff_gui.secondaryExchange.currentText():
                selected_index = self._diff_gui.secondaryExchange.currentIndex()
                self._diff_gui.secondaryExchange.models().item(selected_index).setEnabled(False)
        
        def trade_history(self):
            pass
        
        def top_ten_by_profits(self):
            pass
        
        def write_logs(self):
            pass

        def start_trade(self):
            self._diff_gui.startTradeBtn.setEnabled(False)
            self._diff_gui.stopTradeBtn.setEnabled(True)

        def stop_trade(self):
            self._diff_gui.startTradeBtn.setEnabled(True)
            self._diff_gui.stopTradeBtn.setEnabled(False)


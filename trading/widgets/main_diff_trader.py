from . import *

from DiffTrader.trading.widgets.paths import (ProgramSettingWidgets)
from DiffTrader.trading.settings import AVAILABLE_EXCHANGES, ENABLE_SETTING, UNABLE_SETTING


"""
    controller로 보내야 하는 기준 명확하게 정의해야함.
"""


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
        
        # connect buttons
        self.startTradeBtn.clicked.connect(self.start_trade)
        self.stopTradeBtn.clicked.connect(self.stop_trade)

        # define tab widgets
        self._main_tab = self.MainTab(self)
        self._exchange_setting_tab = self.ExchangeSettingTab(self)
        self._program_setting_tab = self.ProgramSettingTab(self)
    
    def closeEvent(self, *args, **kwargs):
        close_program(self._id)
        self.top_profit_thread.exit()
        self.closed.emit()
    
    def _set_to_ready_trading(self):
        self.startTradeBtn.setEnabled(False)
        self.stopTradeBtn.setEnabled(True)
    
    def start_trade(self):
        self._set_to_ready_trading()
        
        profit_settings = self._program_setting_tab.get_profit_settings()
        
        if not profit_settings:
            profit_settings_error = '프로그램 설정 중 올바르지 못한 설정이 있습니다.'
            self._main_tab.write_logs(profit_settings_error)
            return
        
        min_profit_percent = profit_settings['min_profit_percent']
        min_profit_btc = profit_settings['min_profit_btc']
        auto_withdrawal = profit_settings['auto_withdrawal']
        
    def stop_trade(self):
        self.startTradeBtn.setEnabled(True)
        self.stopTradeBtn.setEnabled(False)

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
            self._diff_gui.profitBTC.text()
            self._diff_gui.profitPercent.text()
            self._diff_gui.tradeHistoryView
            pass
        
        def top_ten_by_profits(self):
            self._diff_gui.profitRankView
            pass
        
        def write_logs(self, log):
            self._diff_gui.logBox
    
    class ExchangeSettingTab(object):
        def __init__(self, diff_gui):
            """
                Args:
                    diff_gui: diffTraderGUI(object)
            """
            self._diff_gui = diff_gui
            self._user_id = diff_gui.user_id
            self._email = diff_gui.email
            self._parent = diff_gui.parent

    class ProgramSettingTab(object):
        def __init__(self, diff_gui):
            """
                Args:
                    diff_gui: diffTraderGUI(object)
            """
            self._diff_gui = diff_gui
            self._user_id = diff_gui.user_id
            self._email = diff_gui.email
            self._parent = diff_gui.parent
        
        def get_profit_settings(self):
            min_profit_percent_str = self._diff_gui.minProfitPercent.text()
            min_profit_btc_str = self._diff_gui.minProfitBTC.text()
            auto_withdrawal = True if self._diff_gui.autoWithdrawal.currentText() == ENABLE_SETTING else False
            
            if min_profit_percent_str and float(min_profit_btc_str) <= 0:
                return dict()
            elif min_profit_btc_str and float(min_profit_btc_str) <= 0:
                return dict()
            # todo 해당 3가지 값이 지속적으로 쓰이는지 모니터링, 지속적으로 쓰이면 object전환 검토
            return dict(min_profit_percent=float(min_profit_percent_str),
                        min_profit_btc=float(min_profit_btc_str),
                        auto_withdrawal=auto_withdrawal)


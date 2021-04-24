from . import *

from DiffTrader.trading.widgets.paths import (ProgramSettingWidgets)
from DiffTrader.trading.settings import AVAILABLE_EXCHANGES, ENABLE_SETTING, UNABLE_SETTING
from DiffTrader.trading.widgets.utils import base_item_setter
from DiffTrader.trading.threads.trade_thread import TradeThread

import logging

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

        primary_config = {
            'key': '',
            'secret': ''
        }

        secondary_config = {
            'key': '',
            'secret': ''
        }

        self.trade_thread = TradeThread(
            email=self.email,

        )

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

            # define table variables
            self.trade_object_set = set()

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
        
        def set_trade_history(self, trade_object):
            """
                거래가 되면, 해당 table로 들어와서, 추가 및 갱신
                history -> db 참조해서 확인 한번 해보기?

                todo: 어떤 history 값들이 들어와야 하는지, 그리고 이전 히스토리 값도 노출이 되어야 하는지?
            """
            self._diff_gui.profitPercent.text()

            item_list = [
                trade_object.symbol,
                trade_object.profit_btc,
                trade_object.profit_percent,
            ]
            row_count = self._diff_gui.tradeHistoryView.rowCount()
            base_item_setter(row_count, self._diff_gui.tradeHistoryView, item_list)
            
            btc_total = [each.profit_btc for each in self.trade_object_set]
            percent_total = [each.profit_percent for each in self.trade_object_set]
            
            total_profit_btc = sum(btc_total)
            total_profit_percent = sum(percent_total) / len(percent_total)
            self._diff_gui.profitBTC.setText(total_profit_btc)
            self._diff_gui.profitPercent.setText(total_profit_percent)
            
        def top_ten_by_profits(self):
            sorted_objects = sorted(self.trade_object_set, key=lambda x: x.profit_btc)
            
            row_count = self._diff_gui.profitRankView.rowCount()
            
            for trade_object in sorted_objects:
                item_list = [
                    trade_object.symbol,
                    trade_object.profit_btc,
                    trade_object.profit_percent,
                ]
                
                base_item_setter(row_count, self._diff_gui.profitRankView, item_list)
                row_count += 1

        def write_logs(self, msg, level=logging.INFO):
            debugger.log(level, msg)
            self._diff_gui.logBox.setText(
                '\n'.join(self._diff_gui.logBox.toPlainText().split('\n')[-500:]) + '\n' + str(msg)
            )
            self._diff_gui.logBox.verticalScrollBar().setValue(
                self._diff_gui.logBox.verticalScrollBar().maximum())

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

            self.config_dict = dict()

            self._diff_gui.bithumbLocalSaveBtn.clicked.connect(self.local_save)
            self._diff_gui.upbitLocalSaveBtn.clicked.connect(self.local_save)
            self._diff_gui.binanceLocalSaveBtn.clicked.connect(self.local_save)

        def local_save(self):
            """
                button 클릭시 상위 group box 가져옴 -> groupBox의 name, 하위의 line edits(key, secret) 값 추출
            """
            parent_widget = self.sender().parent()
            exchange_name = parent_widget.objectName()

            key, secret = {each.text() for each in parent_widget.findChildren(QtWidgets.QLineEdit)}

            exchange_config = {exchange_name: {
                'key': key,
                'secret': secret
            }}

            self.config_dict.update(exchange_config)

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


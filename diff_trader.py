from datetime import datetime

from PyQt5 import QtCore
from PyQt5 import uic

from widgets.exchange_select_widget import *
from widgets.exchanges.bithumb_widget import BithumbWidget
from widgets.exchanges.upbit_widget import UpbitWidget
from widgets.exchanges.binance_widget import BinanceWidget
# from widgets.exchanges.bitfinex_widget import BitfinexWidget
# from widgets.exchanges.huobi_widget import HuobiWidget

from settings_encryptor import *
from widgets.min_profit_widget import *

from DiffTrader.apps.trading.threads.trade_thread import TradeThread
from models import TradeTableModel
from top_profit_thread import TopProfitThread

main_ui = uic.loadUiType(os.path.join(sys._MEIPASS, 'ui/main.ui'), from_imports=True, import_from='ui')[0]


class DiffTraderGUI(QtWidgets.QMainWindow, main_ui):
    closed = QtCore.pyqtSignal()

    def __init__(self, _id, email, parent=None):
        super().__init__()

        self._id = _id
        self.email = email
        self.p = parent

        self.setupUi(self)

        self.primary_exchange_str = None
        self.secondary_exchange_str = None
        self.trade_thread = None

        # add main widget
        self.main_top_widget = MainTopWidget()
        self.main_main_widget = MainMainWidget()
        self.top_layout.addWidget(self.main_top_widget)
        self.main_layout.addWidget(self.main_main_widget)

        # trade history
        self.history_data = []
        self.nid = []
        self.trade_table_model = TradeTableModel(
            ['시간', '거래코인', '거래소 1', '거래소 2', '수익(btc)'],
            self.history_data,
            self.nid
        )
        self.main_main_widget.trade_history_view.setModel(self.trade_table_model)
        self.main_main_widget.trade_history_view.show()

        self.expected_profit = []
        self.nid2 = []
        self.top_profit_model = TradeTableModel(
            ['메인 거래소', '서브 거래소', '차익매매코인', '수익률', '시간'],
            self.expected_profit,
            self.nid2
        )
        self.main_main_widget.top_profit_view.setModel(self.top_profit_model)
        self.main_main_widget.top_profit_view.show()
        self.top_profit_thread = TopProfitThread(self)
        self.top_profit_thread.start()

        # add program setting widget
        self.top_layout.addWidget(QtWidgets.QWidget())
        self.min_profit_widget = MinProfitWidget(_id)
        self.main_layout.addWidget(self.min_profit_widget)

        # exchange settings
        setting_dialog = LoadSettingsDialog()
        setting_data = setting_dialog.exec()

        # add exchange setting widget
        self.exchange_top_widget = ExchangeSelectorWidget()
        self.top_layout.addWidget(self.exchange_top_widget)
        bithumb_widget = BithumbWidget(setting_data)
        upbit_widget = UpbitWidget(setting_data)
        binance_widget = BinanceWidget(setting_data)
        bitfinex_widget = BitfinexWidget(setting_data)
        huobi_widget = HuobiWidget(setting_data)
        self.main_layout.addWidget(bithumb_widget)
        self.main_layout.addWidget(upbit_widget)
        self.main_layout.addWidget(binance_widget)
        self.main_layout.addWidget(bitfinex_widget)
        self.main_layout.addWidget(huobi_widget)
        self.exchange_widgets = {'Bithumb': bithumb_widget, 'UpbitBTC': upbit_widget, 'UpbitUSDT': upbit_widget,
                                 'UpbitKRW': upbit_widget, 'Binance': binance_widget,
                                 'Bitfinex': bitfinex_widget, 'Huobi': huobi_widget}

        self.exchange_top_widget.exchanges.currentIndexChanged.connect(self.show_specific_exchange_setting)
        self.last_setting_idx = 2

        # hide widgets
        self.hide_main_widgets()
        self.hide_program_setting_widgets()
        self.hide_exchange_setting_widgets()

        # connects
        self.go_main_btn.clicked.connect(self.show_main_widgets)
        self.go_exchange_setting_btn.clicked.connect(self.show_exchange_setting_widgets)
        self.go_program_setting_btn.clicked.connect(self.show_program_setting_widgets)

        self.logout_btn.clicked.connect(self.close)

        self.main_top_widget.start_trade_btn.clicked.connect(self.start_trade)
        self.main_top_widget.stop_trade_btn.clicked.connect(self.stop_trade)

        # set settings
        self.num_set = 0 if not setting_data else len(setting_data.keys())

        # show main widget
        self.show_main_widgets()
        self.main_top_widget.stop_trade_btn.setEnabled(False)

    def closeEvent(self, QCloseEvent):
        close_program(self._id)
        self.top_profit_thread.exit()
        self.closed.emit()

    # start trade in QThread
    def start_trade(self):
        try:
            self.main_top_widget.start_trade_btn.setEnabled(False)
            self.main_top_widget.stop_trade_btn.setEnabled(True)
            self.primary_exchange_str = self.main_top_widget.primary_exchange.currentText()
            self.secondary_exchange_str = self.main_top_widget.secondary_exchange.currentText()

            if self.primary_exchange_str == self.secondary_exchange_str:
                QtWidgets.QMessageBox.about(self, "거래소 설정 오류", "거래소 1과 거래소 2가 같을 수 없습니다.")
                self.main_top_widget.start_trade_btn.setEnabled(True)
                self.main_top_widget.stop_trade_btn.setEnabled(False)
                return

            primary_widget = self.exchange_widgets[self.primary_exchange_str]
            secondary_widget = self.exchange_widgets[self.secondary_exchange_str]

            primary_line_edits = primary_widget.findChild(QtWidgets.QGroupBox).findChildren(QtWidgets.QLineEdit)
            primary_cfg = {primary_line_edit.objectName(): primary_line_edit.text()
                           for primary_line_edit in primary_line_edits
                           }
            primary_info = {self.primary_exchange_str: primary_cfg}
            secondary_line_edits = secondary_widget.findChild(QtWidgets.QGroupBox).findChildren(QtWidgets.QLineEdit)
            secondary_cfg = {secondary_line_edit.objectName(): secondary_line_edit.text()
                             for secondary_line_edit in secondary_line_edits
                             }
            secondary_info = {self.secondary_exchange_str: secondary_cfg}

            min_profit_per = self.min_profit_widget.min_pft_per.value()
            min_profit_btc = self.min_profit_widget.min_pft_btc.value()
            auto_withdrawal = self.min_profit_widget.withdraw_setting.currentIndex()
            # Start Thread
            self.trade_thread = TradeThread(self.email, primary_info, secondary_info, min_profit_per, min_profit_btc,
                                            auto_withdrawal)
            self.trade_thread.stopped.connect(self.trade_thread_stopped)
            self.trade_thread.log_signal.connect(self.write_log)
            self.trade_thread.start()
            self.write_log(logging.DEBUG, 'Thread Start')
        except:
            debugger.exception("MAIN")
            self.write_log(logging.ERROR, '거래 시작 실패')

    def stop_trade(self):
        # stop trade QThread
        self.main_top_widget.stop_trade_btn.setEnabled(False)
        self.trade_thread.stop()
        self.write_log(logging.INFO, '거래를 중지합니다. 중지 될 때까지 잠시 기다려주세요.')

    def trade_thread_stopped(self):
        self.main_top_widget.start_trade_btn.setEnabled(True)
        self.write_log(logging.INFO, '거래 중지 성공.')

    def write_log(self, level, msg):
        debugger.log(level, msg)
        if level == logging.INFO:
            self.main_main_widget.log_box.setText(
                '\n'.join(self.main_main_widget.log_box.toPlainText().split('\n')[-500:]) + '\n' + str(msg)
            )
            self.main_main_widget.log_box.verticalScrollBar().setValue(
                self.main_main_widget.log_box.verticalScrollBar().maximum())
        elif level > logging.INFO:
            self.stop_trade()
            QtWidgets.QMessageBox.warning(self,
                                          "처리할 수 없는 오류!", "개발자에게 debugger.log파일을 보내주세요.")

    def update_trade_history(self, trading_coin, profit):
        self.trade_table_model.insertRow(self.trade_table_model.rowCount(), None,
                                         [datetime.now(), trading_coin, self.primary_exchange_str,
                                          self.secondary_exchange_str, profit])

    def show_main_widgets(self):
        self.hide_exchange_setting_widgets()
        self.hide_program_setting_widgets()
        self.top_layout.itemAt(0).widget().show()
        self.main_layout.itemAt(0).widget().show()

        if self.num_set < 2:
            self.num_set = 0
            for key, item in self.exchange_widgets.items():
                if item.is_set():
                    self.num_set += 1

        if self.num_set < 2:
            QtWidgets.QMessageBox.about(self, "설정 필요", "최소 2개 이상의 거래소가 설정 되어 있어야합니다.")
            self.hide_main_widgets()
            self.show_exchange_setting_widgets()

    def hide_main_widgets(self):
        self.top_layout.itemAt(0).widget().hide()
        self.main_layout.itemAt(0).widget().hide()

    def show_program_setting_widgets(self):
        self.hide_main_widgets()
        self.hide_exchange_setting_widgets()
        self.top_layout.itemAt(1).widget().show()
        self.main_layout.itemAt(1).widget().show()

    def hide_program_setting_widgets(self):
        self.top_layout.itemAt(1).widget().hide()
        self.main_layout.itemAt(1).widget().hide()

    def show_exchange_setting_widgets(self):
        self.hide_main_widgets()
        self.hide_program_setting_widgets()
        self.top_layout.itemAt(2).widget().show()
        self.main_layout.itemAt(self.last_setting_idx).widget().show()

    def hide_exchange_setting_widgets(self):
        self.top_layout.itemAt(2).widget().hide()
        for item_idx in range(2, self.main_layout.count()):
            self.main_layout.itemAt(item_idx).widget().hide()

    def show_specific_exchange_setting(self, idx):
        self.hide_exchange_setting_widgets()
        self.last_setting_idx = idx + 2
        self.show_exchange_setting_widgets()


class MainTopWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        uic.loadUi(os.path.join(sys._MEIPASS, 'ui/main_top.ui'), self)


class MainMainWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        uic.loadUi(os.path.join(sys._MEIPASS, 'ui/main_main.ui'), self)


class ProfitChecker(QtCore.QThread):
    def __init__(self):
        super().__init__()

    def run(self):
        while evt.is_set():
            try:

                time.sleep(60)
            except:
                debugger.exception("FATAL. cannot load profit")

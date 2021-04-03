from . import *

from DiffTrader.apps.trading.widgets.utils import save, load
from DiffTrader.apps.trading.widgets.paths import DialogWidgets as widgets


class SettingEncryptKeyDialog(QtWidgets.QDialog, widgets.KEY_DIALOG_WIDGET):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.btn.rejected.connect(self.close)

    def save(self, exchange, **kwargs):
        key = self.enc_key.text()
        success = save(exchange, key, **kwargs)
        if not success:
            self.gui = DifferentKeyInputDialog(exchange, key, **kwargs)
            self.gui.show()
        else:
            QtWidgets.QMessageBox.about(None, "Success", "저장에 성공했습니다.")
            self.close()


class DifferentKeyInputDialog(QtWidgets.QDialog, widgets.CONFIRM_DIALOG_WIDGET):
    def __init__(self, exchange, password, **kwargs):
        super().__init__()
        self.setupUi(self)

        self.btn.rejected.connect(self.close)
        self.btn.accepted.connect(lambda: self.save(exchange, password, **kwargs))

    def save(self, exchange, password, **kwargs):
        os.remove('Settings')
        while os.path.exists('Settings'):
            pass
        success = save(exchange, password, **kwargs)
        if success:
            QtWidgets.QMessageBox.about(None, "Success", "저장에 성공했습니다.")
        else:
            QtWidgets.QMessageBox.about(None, "Failed", "저장에 실패했습니다.")
        self.close()


class LoadSettingsDialog(QtWidgets.QDialog, widgets.KEY_DIALOG_WIDGET):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.data = None
        self.btn.rejected.connect(self.close)
        self.btn.accepted.connect(self.set_data)

    def set_data(self):
        success = load(self.enc_key.text())
        if not success:
            box = QtWidgets.QMessageBox()
            box.setIcon(QtWidgets.QMessageBox.Question)
            box.setWindowTitle('로딩 실패')
            box.setText('암호화키가 틀렸습니다. 세팅파일을 초기화 하시겠습니까?')

            box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            buttonY = box.button(QtWidgets.QMessageBox.Yes)
            buttonY.setText('확인')
            buttonN = box.button(QtWidgets.QMessageBox.No)
            buttonN.setText('취소')
            res = box.exec_()
            if res == 16384:
                os.remove('Settings')
                self.close()
                self.data = False
        else:
            self.data = success

    def exec(self):
        if os.path.exists('Settings'):
            while self.data is None:
                super().exec()
            return self.data
        else:
            return False

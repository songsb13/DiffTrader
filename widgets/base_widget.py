from PyQt5 import QtWidgets
from settings_encryptor import SettingEncryptKeyDialog


class BaseWidgets(QtWidgets.QWidget):
    def __init__(self):
        super(BaseWidgets, self).__init__()
        self.dialog = SettingEncryptKeyDialog()
        self.dialog.btn.accepted.connect(self.save)
        self.showSecretBtn.clicked.connect(self.show_secret)
        self.saveBtn.clicked.connect(self.dialog.show)
        self.saved = False

    def load_key_and_secret(self, exchange_str, data):
        exchange_info = data.get(exchange_str, None)

        if exchange_info:
            self.key.setText(exchange_info['key'])
            self.secret.setText(exchange_info['secret'])

            self.saved = True

    def save(self):
        self.dialog.save(key=self.key.text(), secret=self.secret.text())

        self.saved = True

    def show_secret(self):
        if self.showSecretBox.isChecked():
            self.secret.setEchoMode(0)
        else:
            self.secret.setEchoMode(2)

    def is_set(self):
        if self.key.text() and self.secret.text():
            return True
        else:
            return False

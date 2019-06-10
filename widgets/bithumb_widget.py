from pyinstaller_patch import *
from PyQt5 import QtWidgets, uic
from settings_encryptor import SettingEncryptKeyDialog

WIDGET_PATH = os.path.join(sys._MEIPASS, 'ui/BithumbWidget.ui')

widget = uic.loadUiType(WIDGET_PATH)[0]


class BithumbWidget(QtWidgets.QWidget, widget):
    def __init__(self, data):
        super().__init__()
        self.setupUi(self)
        self.dialog = SettingEncryptKeyDialog()
        self.dialog.btn.accepted.connect(self.save)
        self.checkBox.clicked.connect(self.show_secret)
        self.pushButton.clicked.connect(self.dialog.show)

        self.saved = False

        if data and 'bithumb' in data.keys():
            self.key.setText(data['bithumb']['key'])
            self.secret.setText(data['bithumb']['secret'])
            if 'form' in self.__dict__:
                self.form.setCurrentIndex(data['bithumb']['form'])
                self.KRW_form_value.setValue(data['bithumb']['krw_form_value'])
            self.saved = True

    def save(self):
        if 'form' in self.__dict__:
            self.dialog.save('bithumb', key=self.key.text(),
                             secret=self.secret.text(),
                             form=self.form.currentIndex(),
                             krw_form_value=self.KRW_form_value.value())
        else:
            self.dialog.save('bithumb', key=self.key.text(),
                             secret=self.secret.text())
        self.saved = True

    def show_secret(self):
        if self.checkBox.isChecked():
            self.secret.setEchoMode(0)
        else:
            self.secret.setEchoMode(2)

    def is_set(self):
        if self.key.text() and self.secret.text():
            return True
        else:
            return False

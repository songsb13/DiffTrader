from pyinstaller_patch import *
from widgets.base_widget import BaseWidgets
from settings.widget_paths import ExchangeWidgets as widgets


class BithumbWidget(BaseWidgets, widgets.BITHUMB_WIDGET):
    def __init__(self, data):
        super().__init__()
        self.setupUi(self)

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

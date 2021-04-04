import os
import sys
import requests
import hashlib

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal, QThread
from DiffTrader.trading.widgets.diff_trader import DiffTraderGUI

from Util.pyinstaller_patch import debugger

login_form = uic.loadUiType(os.path.join(sys._MEIPASS, 'backup/ui/Loggin.ui'), from_imports=True, import_from='ui')[0]

VERSION = '0.2.0'


class LoginWidget(QWidget, login_form):
    def __init__(self, pid, widget_after_login):
        super().__init__()
        if 'pydevd' in sys.modules:
            pid = 'SAIDiffTrader'
        self.setupUi(self)
        self.pid = hashlib.sha256(pid.encode()).hexdigest()
        self.widget_after_login = widget_after_login

        self.PassEdit.returnPressed.connect(self.sign_in)
        self.LogginBtn.clicked.connect(self.sign_in)                # 로그인 버튼
        # self.RegisterBtn.clicked.connect(self.register_clicked)     # 회원가입 버튼

    def sign_in(self):                                              # 로그인
        if self.is_valid_form():
            username = self.IdEdit.text()
            password = self.PassEdit.text()

            self.submit(username, password)

    def is_valid_form(self):                                          # 폼 체크
        if self.IdEdit.text() == '':
            QMessageBox.about(self, "Invalid", "아이디를 입력하세요")
            return False

        if self.PassEdit.text() == '':
            QMessageBox.about(self, "Invalid", "비밀번호를 입력하세요")
            return False

        return True

    def submit(self, _id, _pw):
        url = 'http://saiblockchain.com:8877/login'
        try:
            r = requests.post(url, json={'username': _id,
                                         'password': hashlib.sha256(_pw.encode()).hexdigest(),
                                         'program': self.pid})
            data = r.json()
        except:
            QMessageBox.about(self, "Closed", "서버가 닫혀 있습니다.")
            return False

        if data['valid_id'] is False:
            QMessageBox.about(self, "로그인 실패", "아이디가 없거나, 패스워드가 틀렸습니다.")
            return False
        elif data['expired']:
            QMessageBox.about(self, "로그인 실패", "기간이 만료된 ID입니다.\n관리자에게 문의하세요.")
            return False
        elif data['duplicated_connection']:
            box = QMessageBox()
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle('로그인 실패')
            box.setText('다른 네트워크에서 사용중인 ID 입니다.\n다른 네트워크의 연결을 끊고 로그인 하시겠습니까?')

            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            button_yes = box.button(QMessageBox.Yes)
            button_yes.setText('확인')
            button_no = box.button(QMessageBox.No)
            button_no.setText('취소')
            res = box.exec_()
            if res == 16384:
                if self.update_ip(data, first_login=True) is False:
                    return False
            elif res == 65536:
                return False
        else:
            if self.update_ip(data) is False:
                return False

        if data['notice']:
            QMessageBox.about(self, '공지', "{}".format(data['notice']))

        if data['version'] != VERSION:
            QMessageBox.about(self,
                              '공지',
                              ("최신 버전이 아닙니다. 최신버전을 다운로드 해주세요.\n"
                               "현재 버전: {}\n최신 버전: {}").format(VERSION, data['version'])
                              )
            return False

        self.close()
        t = StatusCheck(data['id']) #threading.Thread(target=check_status, args=(data['id'], evt,))
        t.start()
        t.msg.connect(self.status_check_fail)
        try:
            self.mainWidget = self.widget_after_login(_id=data['id'], email=_id)
            self.mainWidget.closed.connect(self.main_closed)
        except:
            debugger.exception("FATAL")
        self.mainWidget.show()

    def update_ip(self, data, first_login=False):
        url = 'http://songsb13.cafe24.com:8877/update_ip'
        try:
            r = requests.post(url, json={'id': data['id'],
                                         'first_login': first_login})
            data = r.json()
        except:
            QMessageBox.about(self, "Closed", "서버가 닫혀 있습니다.")
            return False

        return True

    def main_closed(self):
        self.show()

    def status_check_fail(self, msg):
        QMessageBox.about(self, "Closed", msg)
        self.mainWidget.close()


class StatusCheck(QThread):
    msg = pyqtSignal(str)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def run(self):
        self.msg.emit(check_status(self.user_id, evt))


if __name__ == '__main__':
    try:
        app = QApplication([])
        gui = LoginWidget(pid='SAIDiffTrader', widget_after_login=DiffTraderGUI)
        gui.show()
        app.exec_()
    except:
        debugger.exception("FATAL")
    finally:
        debugger.debug('Done')
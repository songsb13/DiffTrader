import os
import sys

from PyQt5 import uic


class LoginWidgets(object):
    LOGIN = uic.loadUiType(os.path.join(sys._MEIPASS, 'static/guis/Login.ui'), from_imports=True, import_from='ui')[0]

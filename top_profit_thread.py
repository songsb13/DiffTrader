from pyinstaller_patch import *
from datetime import datetime
from PyQt5.QtCore import QThread


class TopProfitThread(QThread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def run(self):
        while True:
            try:
                start = time.time()
                yesterday = start - 24 * 60 * 60
                r = requests.get('http://saiblockchain.com/api/expected_profit',
                                 json={'from': yesterday, 'to': start}
                                 )
                data = r.json()
                if data:
                    for dt in data:
                        dt[-1] = datetime.fromtimestamp(dt[-1]).strftime(
                            '%Y{} %m{} %d{} %H{} %M{}').format('년', '월', '일', '시', '분')
                    self.update_table(data)
                time.sleep(60)
            except:
                debugger.exception("Top Profit Thread ERROR")
                time.sleep(60)

    def update_table(self, rows):
        self.parent.top_profit_model._data = rows
        self.parent.top_profit_model.dataChanged.emit(self.parent.top_profit_model.createIndex(0, 0),
                                                      self.parent.top_profit_model.createIndex(
                                                          self.parent.top_profit_model.rowCount(),
                                                          self.parent.top_profit_model.columnCount()))


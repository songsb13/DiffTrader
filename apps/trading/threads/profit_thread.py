from DiffTrader.apps.trading.threads import QThread, debugger, time
from DiffTrader.apps.trading.apis import get_expected_profit_by_server


class TopProfitThread(QThread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def run(self):
        while True:
            try:
                date_row = get_expected_profit_by_server()
                self.update_table(date_row)
            except:
                debugger.exception("Top Profit Thread ERROR")
                time.sleep(60)

    def update_table(self, rows):
        self.parent.top_profit_model._data = rows
        self.parent.top_profit_model.dataChanged.emit(self.parent.top_profit_model.createIndex(0, 0),
                                                      self.parent.top_profit_model.createIndex(
                                                          self.parent.top_profit_model.rowCount(),
                                                          self.parent.top_profit_model.columnCount()))

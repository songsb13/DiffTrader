from DiffTrader.apps.api_process import UpbitAPIProcess, BinanceAPIProcess


TEST_EXCHANGES = ["Upbit", "Binance"]


for ps in [UpbitAPIProcess, BinanceAPIProcess]:
    ps().start()
#
#
# for each in TEST_EXCHANGES:
#     st = Setter(TEST_USER, each)
#     st.run()

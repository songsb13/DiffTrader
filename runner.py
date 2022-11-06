import os

TEST_EXCHANGES = ["upbit", "binance"]
START_AT = os.path.dirname(os.path.abspath(__file__)) + "/DiffTrader/apps"


def run_file(filename):
    for exchange in TEST_EXCHANGES:
        os.system(f"python {START_AT}/{filename} {exchange} &")


def run_monitoring():
    for n, primary in enumerate(TEST_EXCHANGES):
        for secondary in TEST_EXCHANGES[n:]:
            os.system(f"python {START_AT}/monitoring.py {primary} {secondary} &")


if __name__ == '__main__':
    run_file("api_process.py")
    run_file("setter.py")
    run_monitoring()

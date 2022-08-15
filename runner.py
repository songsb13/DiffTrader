import os

TEST_EXCHANGES = ["upbit", "binance"]


def run_api_processes():
    for exchange in TEST_EXCHANGES:
        os.system(f"python apps/api_process.py {exchange} &")


if __name__ == '__main__':
    run_api_processes()

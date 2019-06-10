#import win_unicode_console
#win_unicode_console.enable()

import asyncio
from upbit2 import UpbitUSDT
from upbit2 import UpbitKRW
from coinone import CoinOne
from bithumb import Bithumb
import configparser
from decimal import Decimal, ROUND_DOWN
import os
import sys
import time
import logging
import requests

# from Util.pyinstaller_patch import *
# main_logger = debugger
main_logger = logging.getLogger(__name__)
main_logger.setLevel(logging.DEBUG)

f_hdlr = logging.FileHandler('huobi_logger.log')
s_hdlr = logging.StreamHandler()

main_logger.addHandler(f_hdlr)
main_logger.addHandler(s_hdlr)

cfg = configparser.ConfigParser()
cfg.read('Settings.ini')

SERVER_URL = "<server-url>"

#main_logger = debugger


def save_profit_expected(profits, currencies, primary_name: str, secondary_name: str):
    """
    :param profits: 예상차익
    :param currencies: 거래될 코인종류
    :param primary_name: 주 거래소 이름
    :param secondary_name: 보조 거래소 이름
    :return: Boolean
    """
    #   m_to_s, s_to_m 정보가 담긴 딕셔너리만 보낸다. 0: primary orderbook, 1: secondary orderbook
    profit = profits[2]
    try:
        r = requests.get(SERVER_URL, json={'profit': profit, 'currencies': currencies, 'primary': primary_name,
                                           'secondary': secondary_name})
        if r.status_code == 200:
            return True
        else:
            return False
    except:
        main_logger.exception("예상차익 저장에러!")
        return False


def find_min_balance(btc_amount, alt_amount, btc_alt, symbol=None):
    btc_amount = Decimal(float(btc_amount)).quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
    alt_btc = Decimal(float(alt_amount) * float(btc_alt['bids'])).quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
    if btc_amount < alt_btc:
        alt_amount = Decimal(float(btc_amount) / float(btc_alt['bids'])).quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
        return btc_amount, alt_amount
    else:
        alt_amount = Decimal(float(alt_amount)).quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
        return alt_btc, alt_amount

#
# def bnc_btm_quantizer(symbol):
#     binance_qtz = binance.get_step_size(symbol)
#     return Decimal(10) ** -4 if binance_qtz < Decimal(10) ** -4 else binance_qtz


async def balance_and_currencies(primary, secondary):
    result = await asyncio.gather(primary.balance(), secondary.balance())

    if 'pydevd' in sys.modules:
        primary_balance = {'XRP': 10000, 'BTC': 1.0, 'DASH': 1.5,} #'ETH': 10, 'BCH': 7, 'LTC': 55, 'XMR': 37, 'ETC': 262,
                           # 'QTUM': 298, 'ZEC': 19, 'EOS': 1000}
        secondary_balance = {'XRP': 10000, 'BTC': 1.0, 'DASH': 1.5, 'ETH': 10, 'BCH': 7, 'LTC': 55, 'XMR': 37, 'ETC': 262,
                           'ZEC': 19}
    else:
        primary_balance, secondary_balance = result
        ts = 0
        err = False
        if not primary_balance[0]:
            main_logger.info(primary_balance[2])
            ts = primary_balance[3]
            err = True
        if not secondary_balance[0]:
            main_logger.info(secondary_balance[2])
            if ts < secondary_balance[3]:
                ts = secondary_balance[3]
            err = True

        if err:
            time.sleep(ts)
            return False

    main_logger.info('[거래소1 잔고] {}'.format(primary_balance))
    main_logger.info('[거래소2 잔고] {}'.format(secondary_balance))
    currencies = list(set(secondary_balance).intersection(primary_balance))
    # if 'EOS' in currencies:
    #     currencies.remove('EOS')
    #   EOS 이체 가능해짐
    main_logger.debug('tradable coins: {}'.format(currencies))
    temp = []
    for c in currencies: # Currency_pair의 필요성(BTC_xxx)
        if c == 'BTC':
            continue
        temp.append('BTC_' + c)
    return [primary_balance, secondary_balance, temp]


async def fees(primary, secondary):
    fut = [
        primary.get_trading_fee(),
        secondary.get_trading_fee(),
        primary.get_transaction_fee(),
        secondary.get_transaction_fee()
    ]
    ret = await asyncio.gather(*fut)
    ts = 0
    err = False
    if not ret[0][0]:
        main_logger.info(ret[0][2])
        ts = ret[0][3]
        err = True
    if not ret[1][0]:
        main_logger.info(ret[1][2])
        if ts < ret[1][3]:
            ts = ret[1][3]
        err = True
    if not ret[2][0]:
        main_logger.info(ret[2][2])
        if ts < ret[2][3]:
            ts = ret[2][3]
        err = True
    if not ret[3][0]:
        main_logger.info(ret[3][2])
        if ts < ret[3][3]:
            ts = ret[3][3]
        err = True
    if err:
        time.sleep(ts)
        return False
    else:
        main_logger.info("수수료 조회 성공")
        return ret[0][1], ret[1][1], ret[2][1], ret[3][1]


async def deposits(primary, secondary):
    result1, result2 = await asyncio.gather(primary.get_deposit_addrs(), secondary.get_deposit_addrs())

    ts = 0
    err = False
    if not result1[0]:
        main_logger.info(result1[2])
        ts = result1[3]
        err = True
    if not result2[0]:
        main_logger.info(result2[2])
        if ts < result2[3]:
            ts = result2[3]
        err = True
    time.sleep(ts)

    if err:
        return False
    else:
        result = (result1[1], result2[1])
        return result

def get_max_profit(data, balance, fee, fee_cnt):
    primary_balance, secondary_balance, currencies = balance
    primary_trade_fee, secondary_trade_fee, primary_tx_fee, secondary_tx_fee = fee
    primary_fee_cnt,secondary_fee_cnt = fee_cnt
    max_profit = None
    primary_orderbook, secondary_orderbook, data = data

    for trade in ['m_to_s', 's_to_m']:
        for currency in currencies:
            alt = currency.split('_')[1]
            if alt not in primary_balance.keys() or not primary_balance[alt]:
                main_logger.info("[거래불가] {} 거래소1 입금 주소가 없습니다.".format(alt))
                continue
            if alt not in secondary_balance.keys() or not secondary_balance[alt]:
                main_logger.info("[거래불가] {} 거래소2 입금 주소가 없습니다.".format(alt))
                continue

            # main_logger.info('[{}-{}] 예상 차익: {}%'.format(currency, trade, data[trade][currency] * 100))
            try:
                if data[trade][currency] < set_percent:
                    #   예상 차익이 %를 넘지 못하는 경우
                    # main_logger.info('[{}-{}] 예상 차익: {}%'.format(alt, trade, data[trade][currency] * 100))
                    # main_logger.info("{currency} 의 예상 차익이 {percent:,}를 넘지 않습니다.".format(currency=currency,
                    #                                                                percent=float(
                    #                                                                    cfg['Profit'][
                    #                                                                        'percent'])))
                    continue
            except ValueError:
                #   float() 이 에러가 난 경우
                main_logger.info("예상 차익 퍼센트는 실수여야만 합니다.")
                return False

            #real_diff 부분은 원화마켓과 BTC마켓의 수수료가 부과되는 횟수가 달라서 거래소 별로 다르게 지정해줘야함
            # 내부에서 부과회수(함수로 만듬 fee_count)까지 리턴해서 받아오는걸로 처리한다.
            real_diff = ((1 + data[trade][currency]) * ((1 - primary_trade_fee) ** primary_fee_cnt) * ((1 - secondary_trade_fee) ** secondary_fee_cnt)) - 1
            try:
                if trade == 'm_to_s':
                    tradable_btc, alt_amount = find_min_balance(primary_balance['BTC'], secondary_balance[alt],
                                                                secondary_orderbook[currency], currency)
                    main_logger.info(
                        '[{}] 거래 가능: 거래소1 {}{} / 거래소2 {}BTC'.format(alt, alt_amount, alt, tradable_btc))

                    btc_profit = (tradable_btc * Decimal(real_diff)) - (
                        Decimal(primary_tx_fee[alt]) * primary_orderbook[currency]['asks']) - Decimal(secondary_tx_fee['BTC'])
                    main_logger.info('[{}] 거래소1 -> 거래소2 수익: {}BTC / {}%'.format(alt, btc_profit, real_diff * 100))

                    # alt_amount로 거래할 btc를 맞춰줌, BTC를 사고 ALT를 팔기때문에 bids가격을 곱해야함
                    # tradable_btc = alt_amount * secondary_orderbook[currency]['bids']
                else:
                    tradable_btc, alt_amount = find_min_balance(secondary_balance['BTC'], primary_balance[alt],
                                                                primary_orderbook[currency], currency)
                    main_logger.info(
                        '[{}] 거래 가능: 거래소2 {}{} / 거래소1 {}BTC'.format(alt, alt_amount, alt, tradable_btc))

                    btc_profit = (tradable_btc * Decimal(real_diff)) - (
                            Decimal(secondary_tx_fee[alt]) * secondary_orderbook[currency][
                        'asks']) - Decimal(primary_tx_fee['BTC'])
                    main_logger.info('[{}] 거래소2 -> 거래소1 수익: {}BTC / {}%'.format(alt, btc_profit, real_diff * 100))

                    # alt_amount로 거래할 btc를 맞춰줌, ALT를 사고 BTC를 팔기때문에 asks가격을 곱해야함
                    # tradable_btc = alt_amount * secondary_orderbook[currency]['asks']

                tradable_btc = tradable_btc.quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
                main_logger.debug('actual trading btc: {}'.format(tradable_btc))
                main_logger.debug('tradable bids/asks: 거래소2: {} 거래소1: {}'.format(secondary_orderbook[currency],
                                                                                       primary_orderbook[currency]))
            except:
                main_logger.exception("FATAL")

            if btc_profit <= min_pft_btc:
                main_logger.info('[{}] 수익이 {} 보다 낮아 거래하지 않습니다.'.format(alt, min_pft_btc))
                #debugger.info('[{}] 수익이 {} 보다 낮아 거래하지 않습니다.'.format(alt, min_pft_btc))
                continue

            if max_profit is None and (tradable_btc != 0 or alt_amount != 0):
                max_profit = [btc_profit, tradable_btc, alt_amount, currency, trade]
            elif max_profit is None:
                pass
            elif max_profit[0] < btc_profit:
                max_profit = [btc_profit, tradable_btc, alt_amount, currency, trade]
            #  최고 이익일 경우, 저장함

    return max_profit

def trade(primary, secondary, max_profit, deposit_addrs, fee):
    """
    :param binance:
    :param bithumb:
    :param max_profit:
    :param bithumb_deposit_addrs:
    :return:
    """
    main_logger.info("최대 이윤 계산결과가 설정한 지정 BTC 보다 높습니다.")
    main_logger.info("거래를 시작합니다.")
    btc_profit, tradable_btc, alt_amount, currency, trade = max_profit
    primary_trade_fee, secondary_trade_fee, primary_tx_fee, secondary_tx_fee = fee
    if auto_withdrawal:
        primary_deposit_addrs, secondary_deposit_addrs = deposit_addrs
        if not primary_deposit_addrs or not secondary_deposit_addrs:
            return False

    alt = currency.split('_')[1]

    if trade == 'm_to_s':
        #   거래소1 에서 ALT 를 사고(btc를팔고) 거래소2 에서 BTC 를 사서(ALT를팔고) 교환함
        res = primary.base_to_alt(currency, float(tradable_btc), float(alt_amount), primary_trade_fee, primary_tx_fee)#,'buy')
        if not res:
            return False

        main_logger.info("거래소1: BTC로 {} 구입".format(alt))
        alt_amount = res

        #무조건 성공해야하는 부분이기때문에 return값이 없다
        secondary.alt_to_base(currency, float(tradable_btc), float(alt_amount))
        main_logger.info('거래소2: {} 판매'.format(alt))

        main_logger.info('거래소2: BTC 구매')
        send_amount = alt_amount + Decimal('{0:g}'.format(primary_tx_fee[alt]))

        if auto_withdrawal:
            while True:
                #   거래소1 -> 거래소2 ALT 이체
                if alt == 'XRP' or alt == 'XMR':
                    res = primary.withdraw(alt, float(send_amount), secondary_deposit_addrs[alt],
                                           secondary_deposit_addrs[alt + 'TAG'])
                else:
                    res = primary.withdraw(alt, float(send_amount), secondary_deposit_addrs[alt])
                if not res[0]:#success 여부
                    main_logger.info("거래소1: {} 이체에 실패 했습니다.".format(alt))
                    main_logger.info("에러내용: " + res[2])
                    time.sleep(res[3])
                else:
                    break
            main_logger.info('거래소1 -> 거래소2 {alt} {unit} 만큼 이동'.format(alt=alt, unit=float(send_amount)))
            send_amount = tradable_btc + Decimal('{0:g}'.format(secondary_tx_fee['BTC']))
            while True:
                #   거래소2 -> 거래소1 BTC 이체
                res = secondary.withdraw('BTC', float(send_amount), primary_deposit_addrs['BTC'])
                if res[0]:
                    break
                else:
                    main_logger.info("Bithumb: BTC 이체에 실패 했습니다.")
                    main_logger.info("에러내용: " + res[2])
                    time.sleep(res[3])
            main_logger.info('거래소2 -> 거래소1 BTC {unit} 만큼 이동'.format(unit=float(send_amount)))
        else:
            main_logger.info("거래가 완료되었습니다. 수동이체 후 아무키나 누르면 다시시작합니다.")
            os.system('PAUSE')
    else:
        #   거래소1 에서 BTC 를 사고 거래소2 에서 ALT 를 사서 교환함
        res = secondary.base_to_alt(currency, float(tradable_btc), float(alt_amount), secondary_trade_fee, secondary_tx_fee)
        if not res:
            return False
        alt_amount = res
        primary.alt_to_base(currency, float(tradable_btc), float(alt_amount))

        main_logger.info('거래소2: {} 구매'.format(alt))

        # 여기서 수수료 1회만 적용, 1회 수수료는 KRW으로 나가기 때문
        # alt_amount *= (1 - Decimal(bithumb_trade_fee))
        # alt_amount *= (1 - Decimal(bithumb_trade_fee))
        # alt_amount -= Decimal(bithumb_tx_fee[alt])
        # alt_amount = alt_amount.quantize(bnc_btm_quantizer(currency), rounding=ROUND_DOWN)

        main_logger.info('거래소1: {}로 BTC 구입'.format(alt))
        send_amount = alt_amount + Decimal('{0:g}'.format(secondary_tx_fee[alt]))

        if auto_withdrawal:
            while True:
                #   Bithumb -> Binance ALT 이체
                if alt == 'XRP' or alt == 'XMR':
                    res = secondary.withdraw(alt, float(send_amount), primary_deposit_addrs[alt],
                                           primary_deposit_addrs[alt + 'TAG'])
                else:
                    res = secondary.withdraw(alt, float(send_amount), primary_deposit_addrs[alt])
                if res[0]:
                    break
                else:
                    main_logger.info("거래소2: {} 이체에 실패 했습니다.".format(alt))
                    main_logger.info("에러내용: " + res[2])
                    time.sleep(res[3])

            main_logger.info('거래소2 -> 거래소1 {alt} {unit} 만큼 이동'.format(
                alt=alt, unit=send_amount
            ))
            send_amount = tradable_btc + Decimal('{0:g}'.format(primary_tx_fee['BTC']))
            while True:
                #   Binance -> Bithumb BTC 이체
                res = primary.withdraw('BTC', float(send_amount), secondary_deposit_addrs['BTC'])
                if not res[0]:
                    main_logger.info("거래소1: BTC 이체에 실패 했습니다.")
                    main_logger.info("에러내용: " + res[2])
                    time.sleep(res[3])
                else:
                    break
            main_logger.info('거래소1 -> 거래소2 BTC {} 만큼 이동'.format(send_amount))
        else:
            main_logger.info("거래가 완료되었습니다. 수동이체 후 아무키나 누르면 다시시작합니다.")
            os.system('PAUSE')

    return True


async def PrimarySecondaryDiffTrader(primary, secondary):
    if auto_withdrawal:
        main_logger.info("출금정보를 가져오는 중입니다...")
        deposit = await deposits(primary, secondary)
        if not deposit:
            sys.exit(1)
        main_logger.info('출금정보 추출 완료.')
    else:
        deposit = None
    # primary_deposit_addrs, secondary_deposit_addrs 가 온다.
    t = 0
    fee = []
    fee_cnt = (primary.fee_count(), secondary.fee_count())

    while True: #evt.is_set():
        try:
            if time.time() >= t + 600:
                fee = await fees(primary, secondary)
                if not fee:
                    #   실패 했을 경우 다시 요청
                    continue
                t = time.time()
            bal_n_crncy = await balance_and_currencies(primary, secondary)
            #   Binance Balance, Bithumb Balance, Common currencies
            if not bal_n_crncy:
                continue
            if not bal_n_crncy[2]:
                #   Intersection 결과가 비어있는 경우
                main_logger.info("거래가능한 코인이 없습니다. 잔고를 확인해 주세요")
                continue
            try:
                if bal_n_crncy[0]['BTC'] > bal_n_crncy[1]['BTC']:
                    default_btc = bal_n_crncy[0]['BTC'] * 1.5
                else:
                    default_btc = bal_n_crncy[1]['BTC'] * 1.5
            except:
                main_logger.info("BTC 잔고가 없습니다. 확인해주세요.")
                #debugger.info("BTC 잔고가 없습니다. 확인해주세요.")
                continue

            #debugger.debug('orderbook 호출')
            # 변경예정 primary__secondary

            #이름변경 compare_otherbook(other(secondary_market,defalut_btc,collection of currencypair)
            #bal_n_crncy를 풀어서 파라메터로 보낸다.
            success, data, err, ts = await primary.compare_orderbook(secondary, bal_n_crncy[2], default_btc)
            #debugger.debug('orderbook 수신완료')
            if not success:
                main_logger.info(err)
                time.sleep(ts)
                continue
            # btc_profit, tradable_btc, alt_amount, currency, trade
            max_profit = get_max_profit(data, bal_n_crncy, fee, fee_cnt)
            #   거래소 이름 가져오도록 설정바람
            primary_name = "거래소1"
            secondary_name = "거래소2"

            if max_profit is None or max_profit is False:
                main_logger.info("만족하는 조건을 찾지 못하였습니다. 조건 재검색...")
                success = save_profit_expected(data, bal_n_crncy[2], primary_name, secondary_name)
                continue
            btc_profit = max_profit[0]

            if 'pydevd' in sys.modules:
                main_logger.info("디버그 모드")
                # continue

            if btc_profit > min_pft_btc:
                #   사용자 지정 BTC 보다 많은경우
                try:
                    success = trade(primary, secondary, max_profit, deposit, fee)
                    if not success:
                        main_logger.info("거래 대기시간이 초과되었습니다. 처음부터 다시 진행합니다.")
                        continue
                    main_logger.info("차익거래에 성공했습니다.")
                except:
                    #   trade 함수 내에서 처리하지 못한 함수가 발견한 경우
                    main_logger.exception("프로그램에 예기치 못한 문제가 발생하였습니다. 로그를 개발자에게 즉시 보내주세요")
                    os.system("PAUSE")
                    #close_program(id_)
                    sys.exit(1)
            else:
                #   사용자 지정 BTC 보다 적은경우
                main_logger.info("최고 이익이 사용자 지정 BTC 보다 작아 거래하지 않습니다.")

            success = save_profit_expected(data, bal_n_crncy[2], primary_name, secondary_name)

        except:
            main_logger.exception("프로그램에 예기치 못한 문제가 발생하였습니다. 로그를 개발자에게 즉시 보내주세요")
            os.system("PAUSE")
            #close_program(id_)
            sys.exit(1)

if __name__ == '__main__':
    # id_ = user_check('gosh', 'gosh1234!', 'BinanceBithumbDiffTrader')
    # id_ = user_check('aramis31', 'aramis311234!', 'BinanceBithumbDiffTrader')
    #id_ = user_check('ceo_b0sCb', 'ceo_b0sCb1234!', 'BinanceBithumbDiffTrader')

    # primary = UpbitUSDT(cfg['Upbit']['username'], cfg['Upbit']['password'], cfg['Upbit']['token'], cfg['Upbit']['chat_id'])
    # primary = CoinOne('77cb1bd8-484b-4472-acb3-bc34f2d10cf6',
    #              '6bbcf2ec-8458-44d0-8dae-0d2d26b9602f',
    #              '489222912:AAG1lgy3WP1IK-ki8oYatb5p3YH3Vcxfctc',
    #              473875582)
    primary = UpbitKRW('namhc302@gmail.com', 's3skagus', '489222912:AAG1lgy3WP1IK-ki8oYatb5p3YH3Vcxfctc',
                      473875582)
    secondary = Bithumb(cfg['Bithumb']['apk_key'], cfg['Bithumb']['secret'])
    # secondary = UpbitUSDT(cfg['Upbit']['username'], cfg['Upbit']['password'], cfg['Upbit']['token'], cfg['Upbit']['chat_id'])

    try:
        set_percent = float(cfg['Profit']['percent'])
        main_logger.debug("최소 %: {}%".format(set_percent))
        set_percent /= 100.0
        min_pft_btc = Decimal(cfg['Profit']['minimum btc'])
        main_logger.debug("최소 btc: {}BTC".format(min_pft_btc))
        auto_withdrawal = cfg['Withdrawal']['auto'].lower() == 'true'
        main_logger.debug("자동 출금: {}".format(auto_withdrawal))
    except:
        main_logger.info("잘못된 값이 설정되어 있습니다. 설정값을 확인해주세요")
        os.system("PAUSE")
        #close_program(id_)
        sys.exit()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(PrimarySecondaryDiffTrader(primary, secondary))
    loop.close()
from pyinstaller_patch import *
import win_unicode_console
win_unicode_console.enable()

import asyncio
from Binance.binance import Binance
from Bithumb.bithumb import Bithumb
import configparser
from decimal import Decimal, ROUND_DOWN


cfg = configparser.ConfigParser()
cfg.read('Settings.ini')

main_logger = debugger


def find_min_balance(btc_amount, alt_amount, btc_alt, symbol):
    btc_amount = Decimal(float(btc_amount)).quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
    alt_btc = Decimal(float(alt_amount) * float(btc_alt['bids'])).quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
    if btc_amount < alt_btc:
        alt_amount = Decimal(float(btc_amount) / float(btc_alt['bids'])).quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
        return btc_amount, alt_amount
    else:
        alt_amount = Decimal(float(alt_amount)).quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
        return alt_btc, alt_amount


def get_max_profit(data, balance, fee, fee_cnt):
    primary_balance, secondary_balance, currencies = balance
    primary_trade_fee, secondary_trade_fee, primary_tx_fee, secondary_tx_fee = fee
    primary_fee_cnt,secondary_fee_cnt = fee_cnt
    max_profit = None
    for trade in ['m_to_s', 's_to_m']:
        for currency in currencies:
            alt = currency.split('_')[1]
            if alt not in primary_balance.keys() or not primary_balance[alt]:
                main_logger.info("[거래불가] {} 거래소1 입금 주소가 없습니다.".format(alt))
                continue
            if alt not in secondary_balance.keys() or not secondary_balance[alt]:
                main_logger.info("[거래불가] {} 거래소2 입금 주소가 없습니다.".format(alt))
                continue

            main_logger.info('[{}-{}] 예상 차익: {}%'.format(currency, trade, data[trade][currency] * 100))
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
                os.system("PAUSE")
                close_program(id_)
                sys.exit(1)

            #real_diff 부분은 원화마켓과 BTC마켓의 수수료가 부과되는 횟수가 달라서 거래소 별로 다르게 지정해줘야함
            # 내부에서 부과회수(함수로 만듬 fee_count)까지 리턴해서 받아오는걸로 처리한다.
            real_diff = ((1 + data[trade][currency]) * ((1 - primary_trade_fee) ** primary_fee_cnt) * ((1 - secondary_trade_fee) ** secondary_fee_cnt)) - 1
            try:
                if trade == 'm_to_s':
                    tradable_btc, alt_amount = find_min_balance(primary_balance['BTC'], secondary_balance[alt],
                                                                data['s_o_b'][currency], currency)
                    main_logger.info(
                        '[{}] 거래 가능: 거래소1 {}{} / 거래소2 {}BTC'.format(alt, alt_amount, alt, tradable_btc))

                    btc_profit = (tradable_btc * Decimal(real_diff)) - (
                        Decimal(primary_tx_fee[alt]) * data['m_o_b'][currency]['asks']) - Decimal(secondary_tx_fee['BTC'])
                    main_logger.info('[{}] 거래소1 -> 거래소2 수익: {}BTC / {}%'.format(alt, btc_profit, real_diff * 100))

                    # alt_amount로 거래할 btc를 맞춰줌, BTC를 사고 ALT를 팔기때문에 bids가격을 곱해야함
                    tradable_btc = alt_amount * data['s_o_b'][currency]['bids']
                else:
                    tradable_btc, alt_amount = find_min_balance(secondary_balance['BTC'], primary_balance[alt],
                                                                data['m_o_b'][currency], currency)
                    main_logger.info(
                        '[{}] 거래 가능: 거래소2 {}{} / 거래소1 {}BTC'.format(alt, alt_amount, alt, tradable_btc))

                    btc_profit = (tradable_btc * Decimal(real_diff)) - (
                            Decimal(secondary_tx_fee[alt]) * data['s_o_b'][currency][
                        'asks']) - Decimal(primary_tx_fee['BTC'])
                    main_logger.info('[{}] 거래소2 -> 거래소1 수익: {}BTC / {}%'.format(alt, btc_profit, real_diff * 100))

                    # alt_amount로 거래할 btc를 맞춰줌, ALT를 사고 BTC를 팔기때문에 asks가격을 곱해야함
                    tradable_btc = alt_amount * data['s_o_b'][currency]['asks']

                tradable_btc = tradable_btc.quantize(Decimal(10)**-4, rounding=ROUND_DOWN)
                main_logger.debug('actual trading btc: {}'.format(tradable_btc))
                main_logger.debug('tradable bids/asks: 거래소2: {} 거래소1: {}'.format(data['s_o_b'][currency],
                                                                                       data['m_o_b'][currency]))
            except:
                debugger.exception("FATAL")

            if btc_profit <= min_pft_btc:
                debugger.info('[{}] 수익이 {} 보다 낮아 거래하지 않습니다.'.format(alt, min_pft_btc))
                continue

            if max_profit is None and (tradable_btc != 0 or alt_amount != 0):
                max_profit = [btc_profit, tradable_btc, alt_amount, currency, trade]
            elif max_profit is None:
                pass
            elif max_profit[0] < btc_profit:
                max_profit = [btc_profit, tradable_btc, alt_amount, currency, trade]
            #  최고 이익일 경우, 저장함
    return max_profit

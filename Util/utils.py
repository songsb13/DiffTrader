from Exchanges.upbit.upbit import BaseUpbit
from Exchanges.binance.binance import Binance
from Exchanges.bithumb.bithumb import BaseBithumb
from DiffTrader.GlobalSetting.settings import REDIS_SERVER, CONFIG, AGREE_WORDS

from Util.pyinstaller_patch import debugger

from decimal import Decimal, getcontext, InvalidOperation
import asyncio
import json
import time
import pickle

getcontext().prec = 8


class FunctionExecutor(object):
    def __init__(self, func, sleep_time=0):
        self._func = func
        self._success = False
        self._trace = list()
        self._sleep_time = sleep_time

    def loop_executor(self, *args, **kwargs):
        self._trace.append('loop_executor')
        debugger.debug(
            'loop_executor, parameter={}, {}'.format(args, kwargs)
        )
        for _ in range(3):
            result = self._func(*args, **kwargs)

            if result.success:
                return result
            time.sleep(self._sleep_time)
        return result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        debugger.debug('Exit FunctionExecutor, trace: [{}]'.format(' -> '.join(self._trace)))
        return None


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


class DecimalDecoder(json.JSONDecoder):
    """
        total_data에 대한 데이터 값은 그대로 있어야 함
        end_line인 경우 string or float, int
        들어올 때 타입확인,
        [3, 4, 6, [3, 4, 7, [6,5,3,3]]]
    """
    def decode_converter(self, type_, tc, dic=False):
        for k in tc:
            if isinstance(k, list):
                type_.append(list())
                self.decode_converter(type_[-1], k)
            elif isinstance(k, dict):
                type_.append(dict())
                self.decode_converter(type_[-1], k, True)
            else:
                if dic:
                    if isinstance(tc[k], list):
                        type_[k] = list()
                        self.decode_converter(type_[k], tc[k])
                    elif isinstance(tc[k], dict):
                        type_[k] = dict()
                        self.decode_converter(type_[k], tc[k], True)
                    else:
                        if isinstance(tc[k], (float, int, str)):
                            try:
                                type_[k] = Decimal(tc[k])
                            except InvalidOperation:
                                type_[k] = tc[k]
                        else:
                            type_[k] = tc[k]
                else:
                    if isinstance(k, (float, int, str)):
                        try:
                            type_.append(Decimal(k))
                        except InvalidOperation:
                            type_.append(k)
                    else:
                        type_.append(k)

    def decode(self, s, _w=None):
        decoded = json.JSONDecoder.decode(self, s)
        if isinstance(decoded, dict):
            decode_with_decimal = dict()
            is_dic = True
        else:
            decode_with_decimal = list()
            is_dic = False
        self.decode_converter(decode_with_decimal, decoded, is_dic)

        return decode_with_decimal


async def task_wrapper(fn_data):
    result = list()
    for data in fn_data:
        fn = data['fn']
        kwargs = data.get('kwargs', dict())
        task = asyncio.create_task(
            fn(**kwargs)
        )
        result.append(await task)

    return result


def publish_redis(key, value, use_decimal=False):
    """
        key: str
        value: dict
    """
    if use_decimal:
        dict_to_json_value = json.dumps(value, cls=DecimalEncoder)
    else:
        dict_to_json_value = json.dumps(value)

    REDIS_SERVER.publish(key, dict_to_json_value)


def subscribe_redis(key):
    """
        (n-1)+(n-2) ... +1
    """
    ps = REDIS_SERVER.pubsub()

    ps.subscribe(key)
    return ps


def get_redis(key, use_decimal=False):
    """
        key: str
    """
    try:
        value = REDIS_SERVER.get(key)

        if not value:
            return None

        if use_decimal:
            json_to_dict_value = json.loads(value, cls=DecimalDecoder)
        else:
            json_to_dict_value = json.loads(value)

        return json_to_dict_value
    except:
        return None


def set_redis(key, value, use_decimal=False):
    """
        key: str
        value: dict
    """
    if use_decimal:
        dict_to_json_value = json.dumps(value, cls=DecimalEncoder)
    else:
        dict_to_json_value = json.dumps(value)

    REDIS_SERVER.set(key, dict_to_json_value)

    return


def get_exchanges():
    obj = dict()
    if CONFIG['Upbit']['Run'].upper() in AGREE_WORDS:
        obj['Upbit'] = BaseUpbit(CONFIG['Upbit']['Key'], CONFIG['Upbit']['Secret'])
    if CONFIG['Binance']['Run'].upper() in AGREE_WORDS:
        obj['Binance'] = Binance(CONFIG['Binance']['Key'], CONFIG['Binance']['Secret'])
    if CONFIG['Bithumb']['Run'].upper() in AGREE_WORDS:
        obj['Bithumb'] = BaseBithumb(CONFIG['Bithumb']['Key'], CONFIG['Bithumb']['Secret'])

    return obj


def get_auto_withdrawal():
    return True if CONFIG['General']['Auto Withdrawal'].upper() in AGREE_WORDS else False


def get_withdrawal_info():
    withdrawal_info = {
        'minimum_profit_amount': CONFIG['General']['Minimum Profit Amount'],
        'balance_withdrawal_percent': CONFIG['General']['Balance Withdrawal Percent']
    }
    return withdrawal_info


def get_min_profit():
    return Decimal(CONFIG['Profit']['Withdrawal Percent']).quantize(Decimal(10) ** -6)


class CustomPickle(object):
    def __init__(self, obj, path):
        try:
            self.load()
        except:
            self.obj = obj
        self.path = path

    def save(self):
        with open(self.path, 'wb') as f:
            return pickle.dump(self.obj, f)

    def load(self):
        with open(self.path, 'rb') as f:
            self.obj = pickle.load(f)


if __name__ == '__main__':
    dd = [{'balance': {'BTC': Decimal('0.00965321'), 'ETH': Decimal('0.79017703'), 'USDT': Decimal('0.23487871'), 'KNC': Decimal('0.07830000'), 'ARK': Decimal('0.00715000'), 'XRP': Decimal('1.20388500'), 'ADA': Decimal('0.27135491'), 'BUSD': Decimal('0.01712369')}, 'deposit': {'BTC': '18tqAJGjchLNCGpm4L3WqdWatB51oTjhPP', 'ETH': '0x817f37daf92fcb3f019bae400fccf3c5b49ed67f'}, 'transaction_fee': {'AGLD': Decimal('25'), 'STPT': Decimal('298'), 'MXN': Decimal('0'), 'UGX': Decimal('0'), 'RENBTC': Decimal('0.000005'), 'GLM': Decimal('76'), 'RAY': Decimal('0.29'), 'NEAR': Decimal('0.016'), 'AUDIO': Decimal('29'), 'HNT': Decimal('0.05'), 'ADADOWN': Decimal('0'), 'CDT': Decimal('246'), 'SPARTA': Decimal('2'), 'SUSD': Decimal('15'), 'FARM': Decimal('0.0019'), 'XNO': Decimal('0.011'), 'AION': Decimal('0.1'), 'NPXS': Decimal('6094'), 'DGB': Decimal('0.2'), 'ZRX': Decimal('45'), 'BCD': Decimal('0.01'), 'EASY': Decimal('0.017'), 'SANTOS': Decimal('0.076'), 'WING': Decimal('0.0027'), 'WNXM': Decimal('0.85'), 'BCH': Decimal('0.001'), 'JST': Decimal('3.16'), 'ADAUP': Decimal('0'), 'HOT': Decimal('6128'), 'AR': Decimal('0.03'), 'IRIS': Decimal('1'), 'RAMP': Decimal('1.77'), 'BCX': Decimal('0.5'), 'SEK': Decimal('0'), 'TRIG': Decimal('50'), 'RCN': Decimal('539'), 'COVER': Decimal('0.005'), 'FLM': Decimal('0.5'), 'GNO': Decimal('0.093'), 'VITE': Decimal('3.83'), 'GNT': Decimal('0'), 'BKRW': Decimal('0'), 'CFX': Decimal('1.45'), 'XPR': Decimal('1'), 'SFP': Decimal('0.24'), 'DIA': Decimal('0.21'), 'RDN': Decimal('126'), 'ACA': Decimal('0.2'), 'ARDR': Decimal('2'), 'LOOMOLD': Decimal('0'), 'NEBL': Decimal('0.01'), 'ACH': Decimal('744'), 'SLPOLD': Decimal('0'), 'BEL': Decimal('0.21'), 'JUV': Decimal('0.01'), 'ACM': Decimal('0'), 'MINA': Decimal('0.5'), 'GRTDOWN': Decimal('0'), 'VTHO': Decimal('200'), 'PYROLD': Decimal('3647'), 'SGB': Decimal('0.01'), 'SALT': Decimal('5.2'), 'STORM': Decimal('100'), 'REN': Decimal('84'), 'REP': Decimal('1.95'), 'ADA': Decimal('1'), 'ELF': Decimal('0.53'), 'REQ': Decimal('115'), 'STORJ': Decimal('22'), 'CHF': Decimal('0'), 'ADD': Decimal('100'), 'BZRX': Decimal('155'), 'SGT': Decimal('200'), 'DF': Decimal('1.87'), 'RARE': Decimal('47'), 'EOSDOWN': Decimal('0'), 'PAXG': Decimal('0.017'), 'YOYO': Decimal('1'), 'PAX': Decimal('0'), 'CHR': Decimal('0.34'), 'VND': Decimal('0'), 'BCHDOWN': Decimal('0'), 'WAVES': Decimal('0.002'), 'CHZ': Decimal('0.98'), 'ADX': Decimal('0.43'), 'XRP': Decimal('0.31'), 'WPR': Decimal('1525'), 'JASMY': Decimal('736'), 'AED': Decimal('0'), 'FIDA': Decimal('0.51'), 'SAND': Decimal('6.58'), 'DKK': Decimal('0'), 'OCEAN': Decimal('0.34'), 'FOR': Decimal('4.29'), 'UMA': Decimal('4.76'), 'DREPOLD': Decimal('661'), 'SCRT': Decimal('0.037'), 'TUSD': Decimal('1'), 'EZ': Decimal('0.078'), 'TKO': Decimal('0.27'), 'WABI': Decimal('208'), 'RGT': Decimal('1.39'), 'IDRT': Decimal('2980'), 'ENG': Decimal('400'), 'ENJ': Decimal('15'), 'UNIDOWN': Decimal('0'), 'YFII': Decimal('0.000083'), 'KZT': Decimal('0'), 'OAX': Decimal('1.53'), 'GRT': Decimal('66'), 'GRS': Decimal('0.2'), 'UND': Decimal('5'), 'HARD': Decimal('0.35'), 'TFUEL': Decimal('1.99'), 'ENS': Decimal('1.49'), 'LEND': Decimal('1'), 'DLT': Decimal('1026'), 'TROY': Decimal('30'), 'XLMUP': Decimal('0'), 'UNI': Decimal('0.018'), 'BTCDOWN': Decimal('0'), 'TLM': Decimal('1.56'), 'HUF': Decimal('0'), 'SBTC': Decimal('0.0005'), 'CKB': Decimal('1'), 'WRX': Decimal('0.22'), 'XTZ': Decimal('0.053'), 'LUNA': Decimal('0.54'), 'ETHDOWN': Decimal('0'), 'AGI': Decimal('83'), 'BCHA': Decimal('0.0035'), 'EON': Decimal('10'), 'EOP': Decimal('5'), 'EOS': Decimal('0.084'), 'GO': Decimal('1'), 'NCASH': Decimal('21273'), 'RIF': Decimal('3'), 'NSBT': Decimal('0.0014'), 'SKL': Decimal('277'), 'XDATA': Decimal('0'), 'GTC': Decimal('4.98'), 'PEN': Decimal('0'), 'BLINK': Decimal('50'), 'SOLO': Decimal('0'), 'SXPDOWN': Decimal('0'), 'HC': Decimal('0.005'), 'SKY': Decimal('0.02'), 'BURGER': Decimal('0.11'), 'NAS': Decimal('0.1'), 'NAV': Decimal('1.13'), 'GTO': Decimal('5.58'), 'WTC': Decimal('53'), 'XVG': Decimal('0.1'), 'EPS': Decimal('1.12'), 'DNT': Decimal('872'), 'CLV': Decimal('0.56'), 'FLOW': Decimal('0.03'), 'XTZDOWN': Decimal('0'), 'XVS': Decimal('0.024'), 'STEEM': Decimal('0.01'), 'BVND': Decimal('6543'), 'SLP': Decimal('20'), 'VRT': Decimal('47'), 'NBS': Decimal('1'), 'DON': Decimal('0.0088'), 'LAZIO': Decimal('0.063'), 'DOT': Decimal('0.0096'), 'IQ': Decimal('50'), 'GRTUP': Decimal('0'), '1INCH': Decimal('0.11'), 'KNCL': Decimal('4'), 'CHESS': Decimal('0.19'), 'MITH': Decimal('5.07'), 'ERD': Decimal('0'), 'DEGO': Decimal('0.05'), 'CND': Decimal('4559'), 'GYEN': Decimal('1216'), 'UNFI': Decimal('0.035'), 'FTM': Decimal('0.099'), 'POWR': Decimal('49'), 'ERN': Decimal('5.58'), 'GVT': Decimal('0.28'), 'WINGS': Decimal('0'), 'FTT': Decimal('0.65'), 'VOXEL': Decimal('0.18'), 'PHA': Decimal('0.78'), 'RLC': Decimal('13'), 'PHB': Decimal('0.72'), 'TRXDOWN': Decimal('0'), 'ATOM': Decimal('0.005'), 'XRPUP': Decimal('0'), 'QUICK': Decimal('0.16'), 'BLZ': Decimal('1.28'), 'SNM': Decimal('0.98'), 'BOBA': Decimal('10'), 'MBL': Decimal('4.1'), 'BNBUP': Decimal('0'), 'MTLX': Decimal('1.5'), 'SNT': Decimal('536'), 'PHP': Decimal('0'), 'SNX': Decimal('0.036'), 'LTCDOWN': Decimal('0'), 'FUN': Decimal('2848'), 'SNMOLD': Decimal('404'), 'COP': Decimal('0'), 'COS': Decimal('12'), 'API3': Decimal('8.34'), 'USD': Decimal('0'), 'QKC': Decimal('11'), 'SUSHIUP': Decimal('0'), 'ROSE': Decimal('0.1'), 'GLMR': Decimal('0.5'), 'XYM': Decimal('0.1'), 'PURSE': Decimal('527'), 'SOL': Decimal('0.0018'), 'TRXUP': Decimal('0'), 'CITY': Decimal('0.021'), 'ETC': Decimal('0.007'), 'BNC': Decimal('0'), 'BNB': Decimal('0.0005'), 'CELR': Decimal('3.67'), 'UST': Decimal('0.21'), 'OGN': Decimal('84'), 'ETH': Decimal('0.003'), 'NEO': Decimal('0'), 'TOMO': Decimal('0.16'), 'CELO': Decimal('0.001'), 'KLAY': Decimal('0.005'), 'AUCTION': Decimal('0.013'), 'BADGER': Decimal('2.6'), 'HIGH': Decimal('0.038'), 'GXS': Decimal('0.3'), 'TRB': Decimal('1.32'), 'BNT': Decimal('0.078'), 'QLC': Decimal('1'), 'LBA': Decimal('10'), 'MDA': Decimal('0.49'), 'BNX': Decimal('0.0087'), 'UTK': Decimal('118'), 'WSOL': Decimal('0.01'), 'HEGIC': Decimal('681'), 'MA': Decimal('0'), 'AMB': Decimal('1'), 'MC': Decimal('0.085'), 'TRU': Decimal('0.95'), 'WBNB': Decimal('0.002'), 'FUEL': Decimal('564'), 'DREP': Decimal('0.28'), 'TRY': Decimal('0'), 'TRX': Decimal('3.22'), 'MDT': Decimal('3.3'), 'NFT': Decimal('45000'), 'MDX': Decimal('0.84'), 'XRPDOWN': Decimal('0'), 'AERGO': Decimal('0.92'), 'EUR': Decimal('0'), 'AMP': Decimal('959'), 'BOT': Decimal('0.000099'), 'NULS': Decimal('0.51'), 'AUTO': Decimal('0.00047'), 'NGN': Decimal('0'), 'ANC': Decimal('0.2'), 'BDOT': Decimal('0'), 'EGLD': Decimal('0.0013'), 'ANTOLD': Decimal('1'), 'SPELL': Decimal('50'), 'PUNDIX': Decimal('35'), 'FXS': Decimal('0.01'), 'PLA': Decimal('8'), 'HNST': Decimal('10'), 'EVX': Decimal('1.5'), 'CRV': Decimal('8.76'), 'BAKE': Decimal('0.29'), 'ANT': Decimal('3.46'), 'NU': Decimal('55'), 'FLUX': Decimal('0.13'), 'ANY': Decimal('0.0085'), 'LINKUP': Decimal('0'), 'SRM': Decimal('11'), 'QISWAP': Decimal('1.06'), 'TORN': Decimal('0.0085'), 'PLN': Decimal('0'), 'QNT': Decimal('0.23'), 'ALICE': Decimal('0.025'), 'OG': Decimal('0.02'), 'MFT': Decimal('4114'), 'OM': Decimal('1.98'), 'BTTOLD': Decimal('400'), 'BETH': Decimal('0.000074'), 'BQX': Decimal('0'), 'WETH': Decimal('0.01'), 'PHBV1': Decimal('35'), 'BETA': Decimal('0.45'), 'BRD': Decimal('107'), 'SSV': Decimal('2.61'), 'BUSD': Decimal('0.5'), 'CTK': Decimal('0.13'), 'ARPA': Decimal('3.02'), 'DOTDOWN': Decimal('0'), 'BRL': Decimal('0'), 'ALCX': Decimal('0.17'), 'CTR': Decimal('35'), 'MATIC': Decimal('0.12'), 'IOTX': Decimal('2.62'), 'SHIB': Decimal('9163'), 'TVK': Decimal('203'), 'FRONT': Decimal('0.4'), 'ZAR': Decimal('0'), 'DOCK': Decimal('5'), 'STX': Decimal('1.5'), 'PNT': Decimal('0.29'), 'QI': Decimal('5'), 'DENT': Decimal('10202'), 'MBOX': Decimal('0.066'), 'SUB': Decimal('0'), 'POA': Decimal('1777'), 'IOST': Decimal('1042'), 'CAKE': Decimal('0.026'), 'ETHUP': Decimal('0'), 'POE': Decimal('56116'), 'OMG': Decimal('5.84'), 'BAND': Decimal('0.01'), 'SUN': Decimal('12'), 'ASTR': Decimal('0'), 'SUNOLD': Decimal('0'), 'BTC': Decimal('0.000005'), 'TWT': Decimal('0.34'), 'NKN': Decimal('113'), 'RSR': Decimal('1519'), 'IOTA': Decimal('0.22'), 'CVC': Decimal('94'), 'REEF': Decimal('17'), 'BTG': Decimal('0.006'), 'MIR': Decimal('0.16'), 'KES': Decimal('0'), 'ARK': Decimal('0.2'), 'LOKA': Decimal('12'), 'CVP': Decimal('0.18'), 'ARN': Decimal('0.26'), 'KEY': Decimal('3983'), 'BTS': Decimal('1'), 'SPARTAOLD': Decimal('2'), 'ARS': Decimal('0'), 'CVX': Decimal('1.06'), 'ONE': Decimal('0'), 'LINKDOWN': Decimal('0'), 'ONG': Decimal('0.04'), 'ANKR': Decimal('2.44'), 'SUSHI': Decimal('0.044'), 'ALGO': Decimal('0.01'), 'SC': Decimal('0.1'), 'WBTC': Decimal('0.00073'), 'ONT': Decimal('0.37'), 'PPT': Decimal('28'), 'ONX': Decimal('5.27'), 'BTTC': Decimal('92990'), 'RUB': Decimal('0'), 'PIVX': Decimal('0.2'), 'ASR': Decimal('0.02'), 'FIRO': Decimal('0.05'), 'AXSOLD': Decimal('0'), 'AST': Decimal('161'), 'MANA': Decimal('9.77'), 'DOTUP': Decimal('0'), 'ATA': Decimal('0.47'), 'MEETONE': Decimal('300'), 'QSP': Decimal('416'), 'ATD': Decimal('100'), 'NMR': Decimal('1.06'), 'MKR': Decimal('0.000092'), 'DODO': Decimal('0.39'), 'LIT': Decimal('0.13'), 'ICP': Decimal('0.0003'), 'ZEC': Decimal('0.0018'), 'ATM': Decimal('0.02'), 'APPC': Decimal('638'), 'JEX': Decimal('10.85'), 'ICX': Decimal('0.02'), 'LOOM': Decimal('2.67'), 'ZEN': Decimal('0.002'), 'KP3R': Decimal('0.033'), 'DOGE': Decimal('1.41'), 'DUSK': Decimal('0.4'), 'ALPHA': Decimal('0.48'), 'BOLT': Decimal('10'), 'SXP': Decimal('0.13'), 'HBAR': Decimal('1'), 'RVN': Decimal('1'), 'MLN': Decimal('0.01'), 'AUD': Decimal('0'), 'LTOOLD': Decimal('93'), 'IDR': Decimal('0'), 'CTSI': Decimal('0.42'), 'KAVA': Decimal('0.055'), 'C98': Decimal('0.12'), 'PSG': Decimal('0.01'), 'HCC': Decimal('0.0005'), 'VIDT': Decimal('0.39'), 'NOK': Decimal('0'), 'AVA': Decimal('0.16'), 'SYS': Decimal('1'), 'COCOS': Decimal('0.15'), 'STRAX': Decimal('0.1'), 'EOSUP': Decimal('0'), 'CZK': Decimal('0'), 'GAS': Decimal('0.005'), 'COVEROLD': Decimal('0.055'), 'AAVEDOWN': Decimal('0'), 'THETA': Decimal('0.12'), 'BCHUP': Decimal('0'), 'WAN': Decimal('0.1'), 'ORN': Decimal('0.052'), 'PERL': Decimal('3.75'), 'XLMDOWN': Decimal('0'), 'MASK': Decimal('0.031'), 'AAVE': Decimal('0.0012'), 'GBP': Decimal('0'), 'PERP': Decimal('0.032'), '1INCHUP': Decimal('0'), 'SXPUP': Decimal('0'), 'YFIDOWN': Decimal('0'), 'BOND': Decimal('0.4'), 'YFI': Decimal('0.0000082'), 'PERLOLD': Decimal('450'), 'MOD': Decimal('5'), 'BICO': Decimal('13'), 'OST': Decimal('2825'), 'XEC': Decimal('2455'), 'YGG': Decimal('0.053'), 'PEOPLE': Decimal('277'), 'AXS': Decimal('0.0035'), 'ZIL': Decimal('3.99'), 'VAI': Decimal('0.8'), 'XEM': Decimal('4'), 'CTXC': Decimal('0.1'), 'KEYFI': Decimal('17'), 'XTZUP': Decimal('0'), 'BIDR': Decimal('2997'), 'BCHSV': Decimal('0.01'), 'AAVEUP': Decimal('0'), 'SUSHIDOWN': Decimal('0'), 'COMP': Decimal('0.0015'), 'ETHBNT': Decimal('5'), 'OMOLD': Decimal('41'), 'OOKI': Decimal('1563'), 'RUNE': Decimal('0.044'), 'FORTH': Decimal('7.79'), 'KMD': Decimal('0.39'), 'GHST': Decimal('14'), 'IDEX': Decimal('1.08'), 'BNBDOWN': Decimal('0'), 'DEXE': Decimal('0.029'), 'AVAX': Decimal('0.01'), 'UAH': Decimal('0'), 'KNC': Decimal('0.1'), 'PROS': Decimal('0.27'), 'PROM': Decimal('0.021'), 'BTCUP': Decimal('0'), 'CHAT': Decimal('0'), 'BGBP': Decimal('2.81'), 'LPT': Decimal('1.01'), 'HIVE': Decimal('0.01'), 'BIFI': Decimal('0.000095'), 'PORTO': Decimal('0.5'), 'SNGLS': Decimal('1753'), 'PYR': Decimal('2.07'), 'WAXP': Decimal('2'), 'DAI': Decimal('1'), 'YFIUP': Decimal('0'), 'DAR': Decimal('0.23'), 'FET': Decimal('0.6'), 'LRC': Decimal('31'), 'REPV1': Decimal('0.1'), 'ADXOLD': Decimal('5'), 'MTH': Decimal('1088'), 'MTL': Decimal('17'), 'VET': Decimal('20'), 'ALPACA': Decimal('0.55'), 'USDT': Decimal('1'), 'USDS': Decimal('0'), 'OXT': Decimal('113'), 'USDP': Decimal('0.8'), 'DASH': Decimal('0.002'), 'NVT': Decimal('0.1'), 'SWRV': Decimal('38'), 'EDO': Decimal('2.23'), 'ILV': Decimal('0.00031'), 'GHS': Decimal('0'), 'BTCST': Decimal('0.013'), 'HKD': Decimal('0'), 'JOE': Decimal('0.1'), 'LSK': Decimal('0.1'), 'KEEP': Decimal('59'), 'CAD': Decimal('0'), 'BEAM': Decimal('0.1'), 'CAN': Decimal('5'), 'DCR': Decimal('0.01'), 'CREAM': Decimal('0.0059'), 'DATA': Decimal('2.56'), 'IMX': Decimal('10'), 'ENTRP': Decimal('10'), 'FILUP': Decimal('0'), 'UNIUP': Decimal('0'), 'LTC': Decimal('0.0017'), 'USDC': Decimal('1'), 'WIN': Decimal('641'), 'LTCUP': Decimal('0'), 'INJ': Decimal('0.046'), 'TCT': Decimal('9.13'), 'PARA': Decimal('0'), 'LTO': Decimal('0.91'), 'VGX': Decimal('14'), 'TRIBE': Decimal('42'), 'NXS': Decimal('0.02'), 'EFI': Decimal('0'), 'DYDX': Decimal('13'), 'AGIX': Decimal('214'), 'INR': Decimal('0'), 'CBK': Decimal('1.2'), 'CBM': Decimal('200'), 'INS': Decimal('52'), 'POND': Decimal('4.26'), 'JPY': Decimal('0'), 'LINA': Decimal('7.49'), 'XLM': Decimal('0.97'), 'LINK': Decimal('0.002'), 'QTUM': Decimal('0.01'), 'FILDOWN': Decimal('0'), 'SUPER': Decimal('0.27'), 'UFT': Decimal('0.37'), 'POLS': Decimal('0.12'), 'KSM': Decimal('0.0011'), 'LUN': Decimal('0'), 'FIL': Decimal('0.0094'), 'POLY': Decimal('59'), 'STMX': Decimal('1736'), 'RNDR': Decimal('8.11'), 'BAL': Decimal('0.015'), 'FIO': Decimal('5'), 'GALA': Decimal('0.66'), 'VIB': Decimal('1072'), 'VIA': Decimal('0.01'), 'FIS': Decimal('0.26'), 'BAR': Decimal('0'), 'RAD': Decimal('5.51'), 'BAT': Decimal('0.22'), 'VRAB': Decimal('100'), 'AKRO': Decimal('2145'), 'NZD': Decimal('0'), 'MOVR': Decimal('0.003'), 'XMR': Decimal('0.0001'), '1INCHDOWN': Decimal('0'), 'COTI': Decimal('0.68')}, 'trading_fee': {'BTC': Decimal('0.0010000000')}, 'fee_count': 1}]
    du = json.dumps(dd, cls=DecimalEncoder)
    dk = json.loads(du, cls=DecimalDecoder)
    # dc = DecimalDecoder()
    # dc.end_line(dc.test, dc.tc)

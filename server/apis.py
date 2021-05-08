from DiffTrader.server.models import ProfitSettingQueries
from flask_restful import Resource
from flask import jsonify, request


class ProfitSettingTable(Resource):
    def get(self):
        # todo 해당부분 리턴 값 확인 필요함.
        args = request.args
        user_id = args.get('user_id', None)

        result = ProfitSettingQueries.get_profit_setting_table(user_id)

        return result

    def put(self):
        args = request.args
        user_id = args.get('user_id', None)

        if user_id is None:
            return
        min_profit_percent = args.get('min_profit_percent')
        min_profit_btc = args.get('min_profit_btc')
        auto_withdrawal = args.get('auto_withdrawal')

        value_list = [user_id, min_profit_percent, min_profit_btc, auto_withdrawal]

        if self._value_validator(value_list):
            ProfitSettingQueries.insert_profit_setting_table(value_list)
            return True
        else:
            return False

    def _value_validator(self, list_):
        for each in list_:
            if not each:
                return False
        else:
            return True

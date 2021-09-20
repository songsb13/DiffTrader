from DiffTrader.server.apis import ProfitSettingTable
from DiffTrader.server.apis import ExpectedProfitTable

from flask import Flask
from flask_cors import CORS
from flask_restful import Api

import json


app = Flask(__name__)
api = Api()

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

api.add_resource(ProfitSettingTable, '/v0/setting/profit-table')
api.add_resource(ExpectedProfitTable, '/v0/trade/expect-profit')
api.init_app(app)

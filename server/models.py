from DiffTrader.server.util import execute_db_many, execute_db


class ProfitSettingQueries(object):
    @staticmethod
    def create_min_profit_data_table():
        query = """
            CREATE TABLE IF NOT EXISTS profit_setting_table(
                user_id = INT PRIMARY KEY,
                min_profit_percent float NOT NULL,
                min_profit_btc float NOT NULL,
                auto_withdrawal boolean NOT NULL
            )
        """

        return execute_db(query)

    @staticmethod
    def get_profit_setting_table(user_id):
        query = """
            SELECT user_id
            FROM profit_setting_table
            WHERE user_id = %s
        """
        return execute_db(query, value=user_id)

    @staticmethod
    def insert_profit_setting_table(value_list):
        query = """
            INSERT INTO profit_setting_table(user_id, min_profit_percent, min_profit_btc, auto_withdrawal)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            min_profit_percent = VALUES(min_profit_percent),
            min_profit_btc = VALUES(min_profit_btc),
            auto_withdrawal = VALUES(auto_withdrawal)
        """
        return execute_db(query, value=value_list)

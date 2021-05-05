class ProfitSettingTable(object):
    @staticmethod
    def create_min_profit_data_table():
        return """
            CREATE TABLE IF NOT EXISTS profit_setting_table(
                user_id = INT PRIMARY KEY,
                min_profit_percent float NOT NULL,
                min_profit_btc float NOT NULL,
                auto_withdrawal boolean NOT NULL
            )
        """

    @staticmethod
    def has_already_exists_profit_setting_table():
        return """
            SELECT user_id
            FROM profit_setting_table
            WHERE user_id = %s
        """

    @staticmethod
    def update_profit_setting_table():
        return """
            UPDATE profit_setting_table 
            set min_profit_percent = %s, auto_withdrawal = %s,
            WHERE user_id = %s
        """

    @staticmethod
    def insert_profit_setting_table():
        return """
            INSERT INTO profit_setting_table(user_id, min_profit_percent, min_profit_btc, auto_withdrawal)
        """

from exchanges.ashare_adapter import TushareAShareAdapter
# from exchanges.binance_adapter import BinanceAdapter
# from exchanges.usstock_adapter import USstockAdapter
from config import config

class ExchangeManager:
    """
    Manages exchange adapters dynamically.
    """

    def __init__(self):
        self.adapters = {
            "tushare": TushareAShareAdapter(),
            # "binance": BinanceAdapter(),
            # "usstock": USstockAdapter(),
        }
        self.default_exchange = config.exchange  # Load default exchange from config

    def get_adapter(self, exchange_name=None):
        """
        Retrieve the correct exchange adapter.
        :param exchange_name: The exchange to use (optional). If None, uses default from config.
        :return: Exchange adapter instance
        """
        exchange_name = exchange_name or self.default_exchange
        adapter = self.adapters.get(exchange_name)

        if adapter is None:
            raise ValueError(f"Unsupported exchange: {exchange_name}")

        return adapter

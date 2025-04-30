from abc import ABC, abstractmethod

class ExchangeBase(ABC):
    def __init__(self, config: dict = None):
        """
        Initialize the exchange adapter with an optional configuration.
        
        :param config: A dictionary containing configuration parameters,
                       such as API keys or other settings.
        """
        self.config = config or {}

    @abstractmethod
    def get_realtime_data(self, symbol: str) -> dict:
        """
        Fetch real-time data for a given symbol.
        
        :param symbol: Stock symbol or other trading symbol
        :return: Real-time data typically as a dictionary
        """
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> dict:
        """
        Fetch historical data for a given symbol within a specified date range.
        
        :param symbol: Stock symbol or other trading symbol
        :param start_date: Start date (format: YYYYMMDD)
        :param end_date: End date (format: YYYYMMDD)
        :return: Historical data typically as a dictionary
        """
        pass

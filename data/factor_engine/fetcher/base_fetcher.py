from abc import ABC, abstractmethod
import pandas as pd

class DataFetcher(ABC):
    """
    Abstract base class for data fetching from different sources.
    """

    @abstractmethod
    def fetch(self, symbols: list, fields: list, start: str, end: str, frequency: str) -> pd.DataFrame:
        """
        Fetch time series data for given symbols and fields within the time range.

        Parameters:
            symbols (list): List of target symbols (e.g., BTCUSDT)
            fields (list): List of required fields (e.g., ["close", "volume"])
            start (str): Start time (e.g., "2024-01-01")
            end (str): End time (e.g., "2024-03-01")
            frequency (str): Frequency (e.g., "1min", "1d")

        Returns:
            pd.DataFrame: MultiIndex DataFrame with shape (time, symbol, field)
        """
        pass

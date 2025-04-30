import pandas as pd
from data.data_standardizer.base_standardizer import BaseStandardizer

class TushareStandardizer(BaseStandardizer):

    def standardize_historical(self, raw_data: dict) -> dict:
        """
        Standardize historical daily market data from Tushare into a unified format.

        Expected input keys:
            - trade_date, ts_code, open, high, low, close, vol, amount, pct_chg

        Returns:
            A dictionary with keys:
            - date, asset, open, close, high, low, volume, amount, pctChg
        """
        df = pd.DataFrame([raw_data]) if isinstance(raw_data, dict) else pd.DataFrame(raw_data)

        # Rename columns for consistency
        df.rename(columns={
            "trade_date": "date",
            "ts_code": "asset",
            "vol": "volume",
            "pct_chg": "pctChg"
        }, inplace=True)

        # Format date field
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")

        # Build standardized output
        standardized_data = {
            "date": df["date"].iloc[0],
            "asset": df["asset"].iloc[0],
            "open": float(df["open"].iloc[0]),
            "close": float(df["close"].iloc[0]),
            "high": float(df["high"].iloc[0]),
            "low": float(df["low"].iloc[0]),
            "volume": float(df["volume"].iloc[0]),
            "amount": float(df["amount"].iloc[0]),
            "pctChg": float(df["pctChg"].iloc[0]) if "pctChg" in df.columns else None
        }

        return standardized_data

    def standardize_realtime(self, raw_data: dict) -> dict:
        """
        Standardize real-time market data from Tushare into the same unified format as historical data.

        Expected input keys:
            - ts_code, trade_time, open, high, low, close, vol, amount, pct_chg (if available)

        Returns:
            A dictionary with keys:
            - date, asset, open, close, high, low, volume, amount, pctChg
        """
        df = pd.DataFrame([raw_data]) if isinstance(raw_data, dict) else pd.DataFrame(raw_data)

        # Rename columns for consistency
        df.rename(columns={
            "ts_code": "asset",
            "trade_time": "date",
            "vol": "volume",
            "pct_chg": "pctChg"
        }, inplace=True)

        # Format date
        df["date"] = pd.to_datetime(df["date"], errors='coerce', utc=True).dt.strftime("%Y-%m-%d")

        # Build standardized output
        standardized_data = {
            "date": df["date"].iloc[0],
            "asset": df["asset"].iloc[0],
            "open": float(df["open"].iloc[0]),
            "close": float(df["close"].iloc[0]),
            "high": float(df["high"].iloc[0]),
            "low": float(df["low"].iloc[0]),
            "volume": float(df["volume"].iloc[0]),
            "amount": float(df["amount"].iloc[0]) if "amount" in df.columns else 0.0,
            "pctChg": float(df["pctChg"].iloc[0]) if "pctChg" in df.columns else None
        }

        return standardized_data

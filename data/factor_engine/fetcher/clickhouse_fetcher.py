from clickhouse_driver import Client
import pandas as pd

class ClickHouseFetcher:
    def __init__(self, host='localhost', port=9000, database='historical_data', user='admin', password='admin123'):
        self.client = Client(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )

    def infer_index_symbols(self, symbols: list[str]) -> list[str]:
        """
        Infer benchmark index symbols based on stock suffixes only.
        If both SH and SZ present, fallback to HS300 (000300.SH).
        """
        suffixes = set()
        for s in symbols:
            if s.endswith(".SH"):
                suffixes.add("SH")
            elif s.endswith(".SZ"):
                suffixes.add("SZ")
            elif s.endswith(".BJ"):
                suffixes.add("BJ")
            else:
                print(f"⚠️ Unknown suffix for {s}, skipping benchmark assignment.")

        inferred_indexes = set()

        if "SH" in suffixes and "SZ" in suffixes:
            inferred_indexes.add("000300.SH")
        else:
            if "SH" in suffixes:
                inferred_indexes.add("000001.SH")
            if "SZ" in suffixes:
                inferred_indexes.add("399001.SZ")
            if "BJ" in suffixes:
                inferred_indexes.add("899050.BJ")

        return list(inferred_indexes)

    def fetch(self, symbols, start, end, fields=None, frequency="1d"):
        if frequency != "1d":
            raise ValueError("Only daily data is supported.")

        time_col = "date"
        symbol_col = "asset"
        default_fields = ["open", "high", "low", "close", "volume", "amount", "pctChg"]
        fields = [f.strip("'\"") for f in fields] if fields else default_fields

        if "amount" not in fields:
            fields.append("amount")

        required_fields = [time_col, symbol_col] + fields
        fields_str = ", ".join(required_fields)
        symbols_str = ",".join([f"'{s}'" for s in symbols])

        query = f"""
        SELECT {fields_str}
        FROM market_data
        WHERE {symbol_col} IN ({symbols_str})
        AND {time_col} >= toDateTime('{start}')
        AND {time_col} <= toDateTime('{end}')
        ORDER BY {time_col}, {symbol_col}
        """

        data = self.client.execute(query)
        df = pd.DataFrame(data, columns=["date", "asset"] + fields)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(by=["asset", "date"]).reset_index(drop=True)

        if 'amount' in df.columns and 'volume' in df.columns and 'vwap' not in df.columns:
            df['vwap'] = df['amount'] / df['volume'].replace(0, pd.NA) / 100

        final_fields = ["asset", "date"] + [
            col for col in ["open", "high", "low", "close", "volume", "amount", "vwap", "pctChg"] if col in df.columns
        ]
        return df[final_fields].reset_index(drop=True)

    def fetch_index(self, symbols, start, end, fields=None):
        """
        Fetch index data based on inferred index symbols.
        """
        inferred_indexes = self.infer_index_symbols(symbols)

        if not inferred_indexes:
            print("⚠️ No valid benchmarks inferred, skipping index fetch.")
            return pd.DataFrame()

        normalized_symbols = []
        for idx in inferred_indexes:
            if "." in idx:
                code, exch = idx.split(".")
                normalized = exch.lower() + code
                normalized_symbols.append(normalized)
            else:
                normalized_symbols.append(idx)

        time_col = "date"
        symbol_col = "asset"
        default_fields = ["open", "high", "low", "close", "volume", "amount", "pctChg"]
        fields = [f.strip("'\"") for f in fields] if fields else default_fields

        if "amount" not in fields:
            fields.append("amount")

        required_fields = [time_col, symbol_col] + fields
        fields_str = ", ".join(required_fields)
        symbols_str = ",".join([f"'{s}'" for s in normalized_symbols])

        query = f"""
        SELECT {fields_str}
        FROM index_data
        WHERE {symbol_col} IN ({symbols_str})
        AND {time_col} >= toDateTime('{start}')
        AND {time_col} <= toDateTime('{end}')
        ORDER BY {time_col}, {symbol_col}
        """

        data = self.client.execute(query)
        df = pd.DataFrame(data, columns=["date", "asset"] + fields)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(by=["asset", "date"]).reset_index(drop=True)

        if 'amount' in df.columns and 'volume' in df.columns and 'vwap' not in df.columns:
            df['vwap'] = df['amount'] / df['volume'].replace(0, pd.NA) / 100

        final_fields = ["asset", "date"] + [
            col for col in ["open", "high", "low", "close", "volume", "amount", "vwap", "pctChg"] if col in df.columns
        ]
        return df[final_fields].reset_index(drop=True)

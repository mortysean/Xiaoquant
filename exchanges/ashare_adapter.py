import tushare as ts
from exchanges.exchange_base import ExchangeBase
from data.data_standardizer.tushare_standardizer import TushareStandardizer
from config import config
from datetime import datetime, timedelta
import time
from pprint import pprint


def convert_daily_range_to_minutely(start_date: str, end_date: str,
                                    start_time: str = "09:00:00", end_time: str = "15:00:00"):
    start_dt = datetime.strptime(start_date, '%Y%m%d').strftime('%Y-%m-%d') + " " + start_time
    end_dt = datetime.strptime(end_date, '%Y%m%d').strftime('%Y-%m-%d') + " " + end_time
    return start_dt, end_dt


class TushareAShareAdapter(ExchangeBase):
    def __init__(self):
        ts.set_token(config.api.tushare_token)
        self.pro = ts.pro_api()
        self.frequency = config.frequency
        self.standardizer = TushareStandardizer()

    def get_realtime_data(self, symbol: str) -> dict:
        try:
            df = ts.realtime_quote(ts_code=symbol, src='dc')
            if df.empty:
                return {"error": f"No real-time data found for {symbol} today."}

            standardized_data = self.standardizer.standardize_realtime(df.iloc[0].to_dict())
            return standardized_data

        except Exception as e:
            print(f"Error in get_realtime_data: {e}")
            return {"error": str(e)}

    def get_all_sh_stocks(self):
        """
        Returns a list of all .SH ts_codes (Shanghai A shares).
        """
        try:
            stock_df = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            return stock_df[stock_df['ts_code'].str.endswith('.SH')]['ts_code'].tolist()
        except Exception as e:
            print(f"❌ Error fetching stock list: {e}")
            return []

    def get_historical_data(self, symbol: str, start_date: str = None, end_date: str = None, fetch_all: bool = True) -> dict:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')

        print(f"🕐 Fetching data range: {start_date} to {end_date} for {symbol}")

        all_data = []
        retries = 5
        chunk_days = 300  # Tushare daily API often limits data volume per call

        current_start = datetime.strptime(start_date, "%Y%m%d")
        final_end = datetime.strptime(end_date, "%Y%m%d")

        while current_start <= final_end:
            current_end = min(current_start + timedelta(days=chunk_days - 1), final_end)
            chunk_start_str = current_start.strftime("%Y%m%d")
            chunk_end_str = current_end.strftime("%Y%m%d")

            for attempt in range(retries):
                try:
                    if self.frequency == 'daily':
                        hist_df = self.pro.daily(ts_code=symbol, start_date=chunk_start_str, end_date=chunk_end_str)
                    elif self.frequency == 'hourly':
                        start_dt, end_dt = convert_daily_range_to_minutely(chunk_start_str, chunk_end_str)
                        hist_df = self.pro.stk_mins(ts_code=symbol, freq='60min', start_date=start_dt, end_date=end_dt)
                    elif self.frequency == 'minutely':
                        start_dt, end_dt = convert_daily_range_to_minutely(chunk_start_str, chunk_end_str)
                        hist_df = self.pro.stk_mins(ts_code=symbol, freq='1min', start_date=start_dt, end_date=end_dt)
                    else:
                        raise ValueError(f"Unsupported frequency: {self.frequency}")

                    if hist_df.empty:
                        print(f"⚠️ No data for {chunk_start_str} to {chunk_end_str}")
                    else:
                        chunk_data = [
                            self.standardizer.standardize_historical(row.to_dict())
                            for _, row in hist_df.iterrows()
                        ]
                        all_data.extend(chunk_data)
                    break  # Exit retry loop on success

                except Exception as e:
                    print(f"❌ Error fetching {chunk_start_str}~{chunk_end_str} (attempt {attempt + 1}): {e}")
                    time.sleep(5)  # Retry after delay

            current_start = current_end + timedelta(days=1)

        if not all_data:
            return {"error": "Historical data is empty after retries"}
        return {"data": all_data}

    def get_index_data(self, index_symbol: str, start_date: str = None, end_date: str = None) -> dict:
        """
        Fetch historical index data using Tushare index_daily interface.
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')

        print(f"🕐 Fetching index data: {index_symbol} from {start_date} to {end_date}")
        all_data = []
        retries = 5
        chunk_days = 8000  # maximum per API call

        current_start = datetime.strptime(start_date, "%Y%m%d")
        final_end = datetime.strptime(end_date, "%Y%m%d")

        while current_start <= final_end:
            current_end = min(current_start + timedelta(days=chunk_days - 1), final_end)
            chunk_start_str = current_start.strftime("%Y%m%d")
            chunk_end_str = current_end.strftime("%Y%m%d")

            for attempt in range(retries):
                try:
                    df = self.pro.index_daily(
                        ts_code=index_symbol,
                        start_date=chunk_start_str,
                        end_date=chunk_end_str
                    )

                    if df.empty:
                        print(f"⚠️ No index data from {chunk_start_str} to {chunk_end_str}")
                    else:
                        for _, row in df.iterrows():
                            standardized = {
                                "date": datetime.strptime(row["trade_date"], "%Y%m%d").strftime("%Y-%m-%d"),
                                "asset": row["ts_code"],
                                "open": row.get("open", 0.0),
                                "high": row.get("high", 0.0),
                                "low": row.get("low", 0.0),
                                "close": row.get("close", 0.0),
                                "volume": row.get("vol", 0.0),
                                "amount": row.get("amount", 0.0),
                                "pctChg": row.get("pct_chg", 0.0)
                            }
                            all_data.append(standardized)
                    break
                except Exception as e:
                    print(f"❌ Error fetching index data ({chunk_start_str}~{chunk_end_str}) attempt {attempt+1}: {e}")
                    time.sleep(5)

            current_start = current_end + timedelta(days=1)

        if not all_data:
            return {"error": "Index data is empty after retries"}
        return {"data": all_data}

    def get_hs300_stocks(self, date: str = None):
        """
        获取某月的沪深300成分股列表（返回 ts_code 列表），默认取今日月份。
        推荐使用 Tushare 的 start_date/end_date 参数。
        """
        try:
            if date is None:
                date = datetime.today()
            else:
                date = datetime.strptime(date.replace("-", ""), "%Y%m%d")

            # 自动定位到该月的第一天和最后一天
            start_date = date.replace(day=1).strftime("%Y%m%d")
            if date.month == 12:
                end_date = date.replace(month=12, day=31).strftime("%Y%m%d")
            else:
                next_month = date.replace(month=date.month + 1, day=1)
                end_date = (next_month - timedelta(days=1)).strftime("%Y%m%d")

            df = self.pro.index_weight(index_code='000300.SH', start_date=start_date, end_date=end_date)

            if df.empty:
                print(f"⚠️ No HS300 data found between {start_date} and {end_date}")
                return []

            ts_codes = df['con_code'].dropna().unique().tolist()
            print(f"✅ 成功获取 {start_date} ~ {end_date} 的沪深300成分股，共 {len(ts_codes)} 支")
            print("📋 示例：", ts_codes[:10])
            return ts_codes

        except Exception as e:
            print(f"❌ Error fetching HS300 stocks: {e}")
            return []


if __name__ == "__main__":
    adapter = TushareAShareAdapter()
    sh_symbols = adapter.get_all_sh_stocks()
    print(f"🔍 Total SH stocks fetched: {len(sh_symbols)}")

    for symbol in sh_symbols:
        print(f"📈 Fetching: {symbol}")
        historical_result = adapter.get_historical_data(symbol)
        pprint({"Historical data": historical_result})
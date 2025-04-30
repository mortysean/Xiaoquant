from exchanges.exchange_manager import ExchangeManager
from data.data_ingestion.redis_cache import RedisCache
from data.data_ingestion.kafka_producer import KafkaProducerClient
from data.data_storage.clickhouse_store import ClickHouseStore  # Using ClickHouse for storage
from config import config
from datetime import datetime, timedelta
from exchanges.ashare_adapter import TushareAShareAdapter
import concurrent.futures
from tqdm import tqdm  # 可选加进度条

class MarketDataProducer:
    def __init__(self):
        self.manager = ExchangeManager()
        self.redis_client = RedisCache()
        self.kafka_client = KafkaProducerClient()
        self.clickhouse_client = ClickHouseStore()  # Initialize ClickHouse storage
        self.exchange_name = config.exchange
        self.symbols = config.symbol.split(",") if isinstance(config.symbol, str) else config.symbol or []
        self.index_symbols = config.index_symbol if isinstance(config.index_symbol, list) else [config.index_symbol] if config.index_symbol else []
        print(f"✅ MarketDataProducer initialized for exchange: {self.exchange_name}")

    def _get_effective_date_range(self, symbol):
        # Use config range, or fallback to recent 10 days if missing
        if config.start_date and config.end_date:
            return config.start_date, config.end_date
        else:
            today = datetime.today()
            end = today.strftime('%Y%m%d')
            start = (today - timedelta(days=10)).strftime('%Y%m%d')
            print(f"🕐 Fetching data range: {start} to {end} for {symbol}")
            return start, end


    def fetch_historical_data(self, max_workers=20):
        """
        Fetches historical market data and stores it in ClickHouse using multithreading.
        
        Args:
            max_workers (int): Maximum number of parallel threads.
        """
        try:
            adapter = self.manager.get_adapter(self.exchange_name)

            def fetch_single(symbol):
                start_date, end_date = self._get_effective_date_range(symbol)
                print(f"🔄 Fetching historical data for: {symbol} from {start_date} to {end_date}")

                try:
                    historical_data = adapter.get_historical_data(symbol, start_date, end_date)

                    if isinstance(historical_data, dict) and "data" in historical_data:
                        historical_data = historical_data["data"]
                    elif isinstance(historical_data, dict) and "error" in historical_data:
                        print(f"❌ Error fetching historical data for {symbol}: {historical_data['error']}")
                        return

                    print(f"✅ Historical data retrieved successfully: {len(historical_data)} records for {symbol}")

                    for data in historical_data:
                        if isinstance(data, dict):
                            self.clickhouse_client.insert_market_data(data)
                        else:
                            print(f"⚠️ Skipping invalid data format for {symbol}: {data}")

                    print(f"✅ Historical data stored in ClickHouse for symbol: {symbol}")

                except Exception as e:
                    print(f"❌ Error fetching {symbol}: {e}")

            # 开线程池
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(tqdm(executor.map(fetch_single, self.symbols), total=len(self.symbols)))

        except Exception as e:
            print(f"❌ MarketDataProducer Error (Historical): {e}")

    def fetch_realtime_data(self):
        """
        Fetches real-time market data, stores it in Redis, and sends it to Kafka.
        """
        try:
            adapter = self.manager.get_adapter(self.exchange_name)
            for symbol in self.symbols:
                print(f"🔄 Fetching real-time data for symbol: {symbol}")
                realtime_data = adapter.get_realtime_data(symbol)

                if isinstance(realtime_data, dict) and "error" in realtime_data:
                    print(f"❌ Error fetching real-time data for {symbol}: {realtime_data['error']}")
                    continue

                print(f"✅ Real-time data retrieved successfully: {realtime_data}")

                self.redis_client.store_data(f"market_data:{symbol}", realtime_data)
                print(f"✅ Real-time data cached in Redis for symbol: {symbol}")

                self.kafka_client.send("market_data", realtime_data)
                self.kafka_client.flush()
                print(f"✅ Real-time data sent to Kafka topic: market_data")

        except Exception as e:
            print(f"❌ MarketDataProducer Error (Real-time): {e}")

    def fetch_index_data(self):
        """
        Fetches historical index data and stores it in ClickHouse index_data table.
        """
        try:
            adapter = self.manager.get_adapter(self.exchange_name)
            for index_symbol in self.index_symbols:
                if not index_symbol or index_symbol.lower() == 'none':
                    print("⚠️ Skipping empty or invalid index_symbol")
                    continue

                start_date, end_date = self._get_effective_date_range(index_symbol)

                print(f"🔄 Fetching index data for: {index_symbol} from {start_date} to {end_date}")
                index_data = adapter.get_index_data(index_symbol, start_date, end_date)

                if isinstance(index_data, dict) and "data" in index_data:
                    index_data = index_data["data"]
                elif isinstance(index_data, dict) and "error" in index_data:
                    print(f"❌ Error fetching index data for {index_symbol}: {index_data['error']}")
                    continue

                print(f"✅ Index data retrieved successfully: {len(index_data)} records for {index_symbol}")

                for data in index_data:
                    if isinstance(data, dict):
                        self.clickhouse_client.insert_index_data(data)
                    else:
                        print(f"⚠️ Skipping invalid index data format: {data}")

                print(f"✅ Index data stored in ClickHouse for index: {index_symbol}")

        except Exception as e:
            print(f"❌ MarketDataProducer Error (Index Data): {e}")

    def close(self):
        """Closes Kafka client upon termination."""
        self.kafka_client.close()
        print("✅ Kafka client closed")

if __name__ == "__main__":
    from exchanges.ashare_adapter import TushareAShareAdapter  # 你的 adapter 路径

    year = 2025

    config.start_date = f"{year}0401"
    config.end_date = f"{year}1231"

    adapter = TushareAShareAdapter()
    hs300_list = adapter.get_hs300_stocks("20220115")  # 记得这个日期不能是节假日或停更日

    config.symbol = hs300_list  # ✅ 关键点：拉取 300 支股票
    config.index_symbol = ["000300.SH"]  # ✅ 基准设置为沪深300

    producer = MarketDataProducer()
    producer.fetch_historical_data()
    producer.fetch_index_data()
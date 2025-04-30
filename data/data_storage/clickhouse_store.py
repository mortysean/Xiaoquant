import threading
from queue import Queue
from clickhouse_driver import Client
from datetime import datetime
import pytz

class ClickHouseStore:
    def __init__(self, host='localhost', port=9000, user='admin', password='admin123', database='historical_data', pool_size=10):
        """
        Initializes ClickHouse client connection pool.
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool_size = pool_size
        self.lock = threading.Lock()
        self.pool = Queue(maxsize=pool_size)

        for _ in range(pool_size):
            client = Client(host=self.host, port=self.port, user=self.user, password=self.password, database=self.database)
            self.pool.put(client)

        self._initialize_tables()
        print(f"✅ ClickHouseStore connection pool initialized with {pool_size} clients.")

    def _initialize_tables(self):
        """Ensure required tables exist."""
        self._execute_with_connection(self._create_or_update_market_data_table)
        self._execute_with_connection(self._create_or_update_index_data_table)

    def _create_or_update_market_data_table(self, client):
        query = """
        CREATE TABLE IF NOT EXISTS market_data (
            date DateTime,
            asset String,
            exchange String,
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            price Float64,
            volume Float64
        ) ENGINE = MergeTree()
        ORDER BY (asset, date);
        """
        client.execute(query)

    def _create_or_update_index_data_table(self, client):
        query = """
        CREATE TABLE IF NOT EXISTS index_data (
            date DateTime,
            asset String,
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume Float64,
            amount Float64,
            pctChg Float64
        ) ENGINE = MergeTree()
        ORDER BY (asset, date);
        """
        client.execute(query)

    def _get_connection(self):
        return self.pool.get()

    def _release_connection(self, client):
        self.pool.put(client)

    def _execute_with_connection(self, func, *args, **kwargs):
        client = self._get_connection()
        try:
            return func(client, *args, **kwargs)
        finally:
            self._release_connection(client)

    def insert_market_data(self, data):
        """Insert market data, dynamic columns + de-duplication."""
        def task(client):
            try:
                if isinstance(data["date"], str):
                    dt = self._parse_date(data["date"])
                    data["date"] = dt

                table_columns = client.execute("DESCRIBE TABLE market_data")
                existing_columns = set(row[0] for row in table_columns)

                for key in data.keys():
                    if key not in existing_columns:
                        if key == "date":
                            alter_query = f"ALTER TABLE market_data ADD COLUMN IF NOT EXISTS {key} DateTime"
                        elif key in {"asset", "exchange"}:
                            alter_query = f"ALTER TABLE market_data ADD COLUMN IF NOT EXISTS {key} String"
                        else:
                            alter_query = f"ALTER TABLE market_data ADD COLUMN IF NOT EXISTS {key} Nullable(Float64)"
                        client.execute(alter_query)
                        print(f"🆕 Added missing column to ClickHouse: {key}")

                # De-duplication check
                where_clause = " AND ".join([f"{k} = %({k})s" for k in data.keys()])
                check_query = f"SELECT 1 FROM market_data WHERE {where_clause} LIMIT 1"
                if client.execute(check_query, data):
                    print(f"⚠️ Data already exists for {data['date']} {data['asset']}, skipping insertion.")
                    return

                column_names = ', '.join(data.keys())
                insert_query = f"INSERT INTO market_data ({column_names}) VALUES"
                values = [tuple(data.values())]
                client.execute(insert_query, values)
                print(f"✅ Data inserted into ClickHouse: {data['asset']} @ {data['date']}")

            except Exception as e:
                print(f"❌ ClickHouseStore Error (Insert Market Data): {e}")

        self._execute_with_connection(task)

    def insert_index_data(self, data):
        """Insert index data (fixed schema)."""
        def task(client):
            try:
                if isinstance(data["date"], str):
                    data["date"] = self._parse_date(data["date"])

                insert_query = """
                INSERT INTO index_data (date, asset, open, high, low, close, volume, amount, pctChg)
                VALUES
                """
                values = [[
                    data["date"],
                    data["asset"],
                    data.get("open", 0.0),
                    data.get("high", 0.0),
                    data.get("low", 0.0),
                    data.get("close", 0.0),
                    data.get("volume", 0.0),
                    data.get("amount", 0.0),
                    data.get("pctChg", 0.0)
                ]]
                client.execute(insert_query, values)
                print(f"✅ Index data inserted: {data['asset']} - {data['date']}")

            except Exception as e:
                print(f"❌ ClickHouseStore Error (Insert Index Data): {e}")

        self._execute_with_connection(task)

    def _parse_date(self, dt_str):
        """Parse date string to UTC datetime."""
        try:
            if "T" in dt_str:
                dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
            elif " " in dt_str:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
                dt = dt.replace(hour=0, minute=0, second=0)
            return dt.replace(tzinfo=pytz.UTC)
        except Exception as e:
            raise ValueError(f"Failed to parse 'date' field: {dt_str}, error: {e}")

    def close(self):
        """Close all ClickHouse connections."""
        while not self.pool.empty():
            client = self.pool.get()
            try:
                client.disconnect()
            except Exception:
                pass
        print("✅ ClickHouseStore connection pool closed.")

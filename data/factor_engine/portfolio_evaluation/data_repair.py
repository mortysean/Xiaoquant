import os
import pandas as pd
from data.data_ingestion.market_data_producer import MarketDataProducer
from data.factor_engine.fetcher.clickhouse_fetcher import ClickHouseFetcher
from utils.utils import project_path  

from config import config

# Step 0: Config
START_DATE = "20250401"
END_DATE = "20250430"
PORTFOLIO_PATH = project_path("data", "factor_engine", "portfolio_evaluation", "backtest", "portfolio.csv"
)

def fetch_missing_assets(missing_assets, start_date, end_date):
    """拉取缺失资产的数据"""
    if not missing_assets:
        print("✅ No missing assets detected. Nothing to fetch.")
        return

    print(f"🚛 Fetching missing assets: {missing_assets}")

    config.start_date = start_date
    config.end_date = end_date
    config.symbol = missing_assets
    config.index_symbol = None  # 不需要动指数

    producer = MarketDataProducer()
    producer.fetch_historical_data()
    producer.close()

if __name__ == "__main__":
    if not os.path.exists(PORTFOLIO_PATH):
        raise FileNotFoundError(f"❌ Portfolio file not found at {PORTFOLIO_PATH}")

    portfolio = pd.read_csv(PORTFOLIO_PATH)
    if "asset" not in portfolio.columns:
        raise ValueError("❌ Portfolio CSV must contain 'asset' column.")

    assets = portfolio["asset"].tolist()

    fetcher = ClickHouseFetcher()
    try:
        price_df = fetcher.fetch(symbols=assets, start=START_DATE, end=END_DATE, fields=["close"])
        available_assets = price_df["asset"].unique().tolist()
        missing_assets = list(set(assets) - set(available_assets))
    except Exception as e:
        print(f"❌ Error fetching from ClickHouse: {e}")
        missing_assets = assets

    if missing_assets:
        print(f"⚠️ Missing assets detected: {missing_assets}")
        fetch_missing_assets(missing_assets, start_date=START_DATE, end_date=END_DATE)
    else:
        print("✅ All portfolio assets have price data. No need to fetch.")

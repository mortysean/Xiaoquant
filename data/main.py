import os
import warnings
import pandas as pd
from datetime import datetime
from utils.utils import project_path

# Step 0: Config
START_DATE = "20240401"
END_DATE = "20250430"
FACTOR_LIB = "Alphas101"
ANALYSIS_MODE = "multi"  # "single" or "multi"
SELECTED_FACTORS = None
OUTPUT_PDF = True
FORCE_FETCH = False
CUSTOM_SYMBOLS = None


def get_target_symbols(start_date: str):
    from exchanges.ashare_adapter import TushareAShareAdapter
    if CUSTOM_SYMBOLS:
        print(f"🔗 Using custom symbols: {CUSTOM_SYMBOLS}")
        return CUSTOM_SYMBOLS
    else:
        print(f"🔗 Fetching HS300 constituents...")
        adapter = TushareAShareAdapter()
        return adapter.get_hs300_stocks(start_date)


def check_clickhouse_missing_symbols(start_date: str, end_date: str, symbols: list):
    from data.factor_engine.fetcher.clickhouse_fetcher import ClickHouseFetcher
    fetcher = ClickHouseFetcher()

    start_dt = pd.to_datetime(start_date) - pd.Timedelta(hours=8)
    end_dt = pd.to_datetime(end_date) + pd.Timedelta(hours=16)

    sql = f"""
    SELECT DISTINCT asset FROM market_data
    WHERE asset IN ({','.join(f"'{s}'" for s in symbols)})
    AND date BETWEEN toDateTime('{start_dt.strftime('%Y-%m-%d %H:%M:%S')}')
                AND toDateTime('{end_dt.strftime('%Y-%m-%d %H:%M:%S')}')
    """
    try:
        df = fetcher.client.query_dataframe(sql)
        if df.empty:
            print("❌ No existing data found. All symbols missing.")
            return symbols

        found_symbols = set(df["asset"].tolist())
        missing = list(set(symbols) - found_symbols)

        if missing:
            print(f"❗ Missing symbols detected: {missing}")
        else:
            print("✅ All symbols are covered in ClickHouse.")
        return missing
    except Exception as e:
        print(f"❌ Error checking ClickHouse data: {e}")
        return symbols


def fetch_missing_data(missing_symbols: list, start_date: str, end_date: str):
    from data.data_ingestion import market_data_producer
    from config import config

    if not missing_symbols:
        print("✅ No missing symbols to fetch. Skipping data fetch.")
        return

    print(f"🚛 Fetching missing symbols: {missing_symbols}")
    config.start_date = start_date
    config.end_date = end_date
    config.symbol = missing_symbols
    config.index_symbol = None

    producer = market_data_producer.MarketDataProducer()
    producer.fetch_historical_data()
    producer.fetch_index_data()
    producer.close()


def split_year_ranges(start_date: str, end_date: str):
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    splits = []
    for y in range(start.year, end.year + 1):
        y_start = max(start, datetime(y, 1, 1))
        y_end = min(end, datetime(y, 12, 31))
        splits.append((str(y), y_start.strftime("%Y%m%d"), y_end.strftime("%Y%m%d")))
    return splits


def find_factor_files(base_dir, years, selected=None):
    factor_files = []
    for year in years:
        year_dir = os.path.join(base_dir, str(year))
        if not os.path.exists(year_dir):
            continue
        for dirpath, _, filenames in os.walk(year_dir):
            for fname in filenames:
                if fname.endswith(".csv") and (selected is None or fname.split(".")[0] in selected):
                    factor_files.append(os.path.join(dirpath, fname))
    return factor_files


if __name__ == "__main__":
    warnings.filterwarnings("ignore")

    # Step 1: 获取目标股票池
    target_symbols = get_target_symbols(START_DATE)

    # Step 2: 检查 ClickHouse 中数据缺失情况
    print("\n🔍 [Step 1] Checking ClickHouse missing symbols...")
    missing_symbols = check_clickhouse_missing_symbols(START_DATE, END_DATE, target_symbols)

    if missing_symbols or FORCE_FETCH:
        print("\n🚛 [Step 2] Fetching missing historical data...")
        fetch_missing_data(missing_symbols, START_DATE, END_DATE)
    else:
        print("✅ Historical data already exists. Skipping data fetch.")

    # Step 3: 按年份进行因子计算
    print("\n🧮 [Step 3] Computing factors...")
    from data.factor_engine import main as factor_engine_main
    executor_cls = (
        factor_engine_main.Alphas101 if FACTOR_LIB == "Alphas101" else factor_engine_main.Alphas191
    )
    executor = factor_engine_main.ClassFactorExecutor(cls=executor_cls)

    year_splits = split_year_ranges(START_DATE, END_DATE)
    for year, year_start, year_end in year_splits:
        print(f"\n🔧 Running factor computation for {year} ({year_start} ~ {year_end})...")
        executor.run_all(year=year, list_assets=target_symbols)

    # Step 4: 执行统一因子分析（只分析一次）
    print(f"\n📊 [Step 4] Analyzing factors once from {START_DATE} to {END_DATE} ...")

    if ANALYSIS_MODE == "single":
        if not SELECTED_FACTORS or len(SELECTED_FACTORS) != 1:
            raise ValueError("❌ Single factor analysis requires exactly one factor in SELECTED_FACTORS.")
        from data.factor_engine.factor_analysis import single_factor_analysis
        factor_id = SELECTED_FACTORS[0].replace("alpha", "").zfill(3)
        year = START_DATE[:4]
        alpha_path = project_path("data", "factor_engine", "alphas", FACTOR_LIB, year, f"alpha{factor_id}.csv")
        if not os.path.exists(alpha_path):
            raise FileNotFoundError(f"❌ Factor file not found: {alpha_path}")
        runner = single_factor_analysis.FactorAnalysisRunner(alpha_path=alpha_path)
        runner.run(generate_pdf=OUTPUT_PDF)

    elif ANALYSIS_MODE == "multi":
        from data.factor_engine.factor_analysis import multi_factor_analysis

        factor_root = project_path("data", "factor_engine", "alphas", FACTOR_LIB)
        all_years = [y for y, _, _ in year_splits]
        all_factor_files = find_factor_files(factor_root, years=all_years, selected=SELECTED_FACTORS)

        if not all_factor_files:
            raise ValueError("❌ No valid factor files found for multi-factor analysis.")

        runner = multi_factor_analysis.MultiFactorAnalysisRunner(
            factor_paths=all_factor_files,
            factor_lib_name=FACTOR_LIB,
        )
        runner.run(start_date_str=START_DATE, end_date_str=END_DATE)

    else:
        raise ValueError(f"❌ Invalid ANALYSIS_MODE: {ANALYSIS_MODE}")

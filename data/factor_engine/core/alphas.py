import pandas as pd
from multiprocessing import Pool
from data.factor_engine.fetcher.clickhouse_fetcher import ClickHouseFetcher
from utils.utils import project_path   
import os
import traceback
import time

class Alphas(object):
    def __init__(self, df_data):
        self.data = df_data  # pivot-format DataFrame

    @classmethod
    def calc_alpha(cls, path, func, data):
        try:
            t1 = time.time()
            res = func(data)

            # ✅ 从路径中提取年份
            year = os.path.basename(os.path.dirname(path))
            start_date = f"{year}0101"
            end_date = f"{year}1231"
            res = res[
                (res.index >= pd.to_datetime(start_date)) &
                (res.index <= pd.to_datetime(end_date))
            ]

            res.to_csv(path)
            t2 = time.time()
            print(f"Factory {os.path.splitext(os.path.basename(path))[0]} time {t2 - t1}")
        except Exception as e:
            print(f"generate {path} error!!!")
            traceback.print_exc()


    @classmethod
    def get_stocks_data(cls, year, list_assets, benchmark):
        yer = int(year)
        start_time = f'{yer - 1}-01-01'
        end_time = f'{yer + 1}-01-01'

        fetcher = ClickHouseFetcher()
        df_all = fetcher.fetch(symbols=list_assets, start=start_time, end=end_time)
        df_index = fetcher.fetch_index(symbols=[benchmark], start=start_time, end=end_time)

        # Rename benchmark columns
        df_index = df_index.rename(columns={
            "date": "benchmark_date",
            "open": "benchmark_open",
            "close": "benchmark_close",
            "high": "benchmark_high",
            "low": "benchmark_low",
            "volume": "benchmark_vol",
            "vwap": "benchmark_vwap",
        })

        df = df_all.merge(df_index, how='left', left_on='date', right_on='benchmark_date', suffixes=('', '_bm'))

        df = df.drop(columns=['benchmark_date'])

        # Return pivoted data for wide-format factor computation
        print("当前 DataFrame 列为：", df.columns.tolist())
        df_all = df[["asset", "date", "open", "close", "high", "low", "volume", "amount", "vwap", "pctChg", 
                     "benchmark_open", "benchmark_close"]]
        df_all = df_all[df_all['asset'].notnull()].reset_index(drop=True)
        return df_all.pivot(index='date', columns='asset')

    @classmethod
    def get_benchmark(cls, year, code):
        yer = int(year)
        start_time = f'{yer - 1}-01-01'
        end_time = f'{yer + 1}-01-01'

        fetcher = ClickHouseFetcher()
        df_index = fetcher.fetch_index(symbols=[code], start=start_time, end=end_time)
        return df_index

    @classmethod
    def get_alpha_methods(cls, self):
        return list(filter(lambda m: m.startswith("alpha") and callable(getattr(self, m)), dir(self)))
    
    @classmethod
    def generate_alpha_single(cls, alpha_name, year, list_assets, benchmark, need_save=False):
        stock_data = cls.get_stocks_data(year, list_assets, benchmark)
        stock = cls(stock_data)
        factor = getattr(cls, alpha_name)
        if factor is None:
            print('alpha name is error!!!')
            return None

        alpha_data = factor(stock)

        if need_save:
            # ✅ 过滤该年份数据
            start_date = f"{year}0101"
            end_date = f"{year}1231"
            alpha_data = alpha_data[
                (alpha_data.index >= pd.to_datetime(start_date)) &
                (alpha_data.index <= pd.to_datetime(end_date))
            ]

            path = project_path('data', 'factor_engine', 'alphas', cls.__name__, str(year))
            os.makedirs(path, exist_ok=True)
            alpha_data.to_csv(os.path.join(path, f'{alpha_name}.csv'))


        return alpha_data

    @classmethod
    def generate_alphas(cls, year, list_assets, benchmark):
        import time  # 确保有 time
        from multiprocessing import Pool
        import traceback

        t1 = time.time()
        stock_data = cls.get_stocks_data(year, list_assets, benchmark)
        stock = cls(stock_data)

        path = project_path('data', 'factor_engine', 'alphas', cls.__name__, str(year))  # ✅ 改这里
        os.makedirs(path, exist_ok=True)

        count = os.cpu_count()
        pool = Pool(count)
        methods = cls.get_alpha_methods(cls)

        for m in methods:
            factor = getattr(cls, m)
            try:
                output_file = os.path.join(path, f'{m}.csv')
                pool.apply_async(cls.calc_alpha, (output_file, factor, stock))
            except Exception as e:
                traceback.print_exc()

        pool.close()
        pool.join()
        t2 = time.time()
        print(f"Total time {t2 - t1}")
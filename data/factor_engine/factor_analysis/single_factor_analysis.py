import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from alphalens import performance as perf
from alphalens import tears
from data.factor_engine.fetcher.clickhouse_fetcher import ClickHouseFetcher
from report_output import FactorPDFReport
from utils.utils import project_path  # ✅ 新增导入


class FactorAnalysisRunner:
    def __init__(self, alpha_path: str, quantiles=5, periods=(1, 5, 10)):
        self.alpha_path = alpha_path
        self.factor_filename = os.path.splitext(os.path.basename(alpha_path))[0]
        self.quantiles = quantiles
        self.periods = periods
        self.output_path = project_path("data", "factor_engine", "factor_analysis", "analysis", "alphas", f"{self.factor_filename}_diag")
        os.makedirs(self.output_path, exist_ok=True)

    def check_tearsheet_images_exist(self):
        required_files = [
            "tear_sheet_performance.png",
            "tear_sheet_ic.png",
            "tear_sheet_turnover.png"
        ]
        return all(os.path.exists(os.path.join(self.output_path, f)) for f in required_files)

    def load_and_prepare_factor(self):
        print("📥 Step 1: Loading factor file...")
        df = pd.read_csv(self.alpha_path, index_col=0, parse_dates=True)
        df.index.name = "date"
        df_long = df.reset_index().melt(id_vars=["date"], var_name="asset", value_name="factor")
        df_long["date"] = pd.to_datetime(df_long["date"])
        df_long = df_long.set_index(["date", "asset"]).sort_index()

        valid_dates = df_long.reset_index().groupby("date")["factor"].nunique()
        valid_dates = valid_dates[valid_dates >= self.quantiles].index
        df_long = df_long[df_long.index.get_level_values("date").isin(valid_dates)]

        print(f"✅ Kept {len(valid_dates)} valid dates after filtering")

        df_long["factor"] = df_long.groupby("date")["factor"].rank(pct=True, method="first")
        df_long["factor_quantile"] = df_long.groupby("date")["factor"].transform(
            lambda x: pd.qcut(x, self.quantiles, labels=False, duplicates="drop") + 1
        )
        return df_long

    def fetch_price_data(self, df_factor_long):
        print("💹 Step 2: Fetching price data...")
        start_date = df_factor_long.index.get_level_values("date").min().strftime('%Y-%m-%d')
        end_date_raw = df_factor_long.index.get_level_values("date").max()
        max_horizon = max(self.periods)
        end_date = (end_date_raw + pd.Timedelta(days=max_horizon * 2)).strftime('%Y-%m-%d')

        symbols = df_factor_long.index.get_level_values("asset").unique().tolist()
        fetcher = ClickHouseFetcher()
        df_price = fetcher.fetch(symbols=symbols, start=start_date, end=end_date, fields=["close"])
        df_close = df_price.pivot(index="date", columns="asset", values="close").sort_index()
        df_close = df_close.ffill().bfill()
        return df_close

    def compute_forward_returns(self, factor, prices):
        print("⏩ Step 3: Computing forward returns...")
        asset_list = factor.index.get_level_values("asset").unique()
        prices = prices[asset_list].copy().sort_index()

        results = []
        for period in self.periods:
            fwd_ret = prices.shift(-period) / prices - 1
            fwd_ret = fwd_ret.stack()
            fwd_ret.name = f"{period}D"
            results.append(fwd_ret)

        df_returns = pd.concat(results, axis=1)
        df_returns.index.names = ["date", "asset"]

        df_merged = factor.to_frame(name="factor").join(df_returns, how="left")
        return df_merged

    def run(self, generate_pdf: bool = True):
        print("🚀 Starting Alphalens analysis...")

        if self.check_tearsheet_images_exist():
            print("✅ Found existing tear sheet images, skipping analysis.")
        else:
            print("📊 No tear sheets found. Running Alphalens analysis...")
            df_factor_long = self.load_and_prepare_factor()
            df_close = self.fetch_price_data(df_factor_long)
            factor_data = self.compute_forward_returns(df_factor_long["factor"], df_close)

            factor_data["factor_quantile"] = factor_data.groupby("date")["factor"].transform(
                lambda x: pd.qcut(x, q=self.quantiles, labels=False, duplicates="drop") + 1
            )

            # ✅ 清理 inf / nan 值以防止 OLS 回归报错
            factor_data.replace([np.inf, -np.inf], pd.NA, inplace=True)
            factor_data.dropna(inplace=True)

            figure_count = 0
            original_show = plt.show

            def patched_show():
                nonlocal figure_count
                semantic_names = [
                    "tear_sheet_performance.png",
                    "tear_sheet_ic.png",
                    "tear_sheet_turnover.png"
                ]
                if figure_count < len(semantic_names):
                    filename = semantic_names[figure_count]
                else:
                    filename = f"tear_sheet_{figure_count:02d}.png"

                path = os.path.join(self.output_path, filename)
                plt.savefig(path, dpi=300, bbox_inches='tight')
                print(f"🖼 Saved: {path}")
                plt.close()
                figure_count += 1

            plt.show = patched_show

            with plt.rc_context({'figure.figsize': (12, 8)}):
                tears.create_full_tear_sheet(
                    factor_data,
                    long_short=False,
                    group_neutral=False
                )
            plt.show = original_show
            print("✅ Alphalens analysis completed.")

        if generate_pdf:
            print("📄 Generating PDF report...")
            pdf_report = FactorPDFReport(factor_name=self.factor_filename, output_dir=self.output_path)
            pdf_report.generate()
        else:
            print("📝 Skipping PDF generation as requested.")


if __name__ == "__main__":
    from utils.utils import project_path  # ✅ 加入路径构造

    factor_lib = "Alphas101"
    factor_id = "002"
    year = "2025"

    alpha_path = project_path("data", "factor_engine", "alphas", factor_lib, year, f"alpha{factor_id}.csv")
    print(f"🔗 Using alpha file: {alpha_path}")

    runner = FactorAnalysisRunner(alpha_path=alpha_path)
    runner.run()

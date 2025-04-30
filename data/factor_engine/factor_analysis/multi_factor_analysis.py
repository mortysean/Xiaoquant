import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from alphalens import performance as perf
from data.factor_engine.fetcher.clickhouse_fetcher import ClickHouseFetcher
from utils.utils import project_path


class MultiFactorAnalysisRunner:
    def __init__(self, factor_paths: list[str], factor_lib_name: str, quantiles=5, periods=(1, 5, 10)):
        self.factor_paths = factor_paths
        self.quantiles = quantiles
        self.periods = periods
        self.factor_lib_name = factor_lib_name
        self.output_path = project_path("data", "factor_engine", "factor_analysis", "analysis", "multi_factor", self.factor_lib_name)
        os.makedirs(self.output_path, exist_ok=True)
        self.summary = []

    def load_and_prepare_factors(self, trading_dates):
        print("\U0001F4E5 Loading factor files...")
        factor_frames = []
        for path in self.factor_paths:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            df.index.name = "date"
            factor_name = os.path.basename(path).split(".")[0]
            df_long = df.reset_index().melt(id_vars=["date"], var_name="asset", value_name="factor")
            df_long["factor_name"] = factor_name
            factor_frames.append(df_long)
        df_all = pd.concat(factor_frames)
        df_all = df_all.dropna().set_index(["date", "asset"]).sort_index()
        df_all = df_all[df_all.index.get_level_values("date").isin(trading_dates)]
        return df_all

    def fetch_price_data(self, df_factor_long):
        print("\U0001F4B9 Fetching price data...")
        start_date = df_factor_long.index.get_level_values("date").min().strftime('%Y-%m-%d')
        end_date_raw = df_factor_long.index.get_level_values("date").max()
        end_date = (end_date_raw + pd.Timedelta(days=max(self.periods) * 2)).strftime('%Y-%m-%d')
        symbols = df_factor_long.index.get_level_values("asset").unique().tolist()
        fetcher = ClickHouseFetcher()
        df_price = fetcher.fetch(symbols=symbols, start=start_date, end=end_date, fields=["close"])
        df_close = df_price.pivot(index="date", columns="asset", values="close").sort_index()
        df_close = df_close.ffill().bfill()
        return df_close

    def compute_forward_returns(self, factor, prices):
        print("\u23E9 Computing forward returns...")
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

    def analyze_single_factor(self, name, group, df_close):
        print(f"\n\U0001F4CA Analyzing factor: {name}")
        group = group.drop(columns=["factor_name"])
        factor_series = group["factor"]

        asset_list = factor_series.index.get_level_values("asset").unique()
        valid_assets = [a for a in asset_list if a in df_close.columns]
        missing_assets = set(asset_list) - set(valid_assets)

        if not valid_assets:
            print(f"⚠️ Skipping {name} because all assets missing in df_close.")
            with open(os.path.join(self.output_path, "error_log.txt"), "a") as f:
                f.write(f"{name}: all assets missing in df_close\n")
            return

        if missing_assets:
            print(f"⚠️ {name}: {len(missing_assets)} assets missing from df_close. (e.g. {list(missing_assets)[:5]})")

        df_close_filtered = df_close[valid_assets]
        df_close_filtered = df_close_filtered.dropna(axis=1, thresh=len(df_close_filtered) * 0.8)

        if df_close_filtered.empty:
            print(f"⚠️ Skipping {name} because no sufficient price data.")
            with open(os.path.join(self.output_path, "error_log.txt"), "a") as f:
                f.write(f"{name}: insufficient price data\n")
            return

        factor_data = self.compute_forward_returns(factor_series, df_close_filtered)
        factor_data = factor_data.dropna()

        if factor_data.empty or factor_data["factor"].nunique() < self.quantiles:
            print(f"⚠️ Skipping {name} because factor_quantile splitting failed.")
            with open(os.path.join(self.output_path, "error_log.txt"), "a") as f:
                f.write(f"{name}: factor_quantile splitting failed\n")
            return

        factor_data["factor_quantile"] = factor_data.groupby("date")["factor"].transform(
            lambda x: pd.qcut(x, self.quantiles, labels=False, duplicates="drop") + 1
        )

        ic_list = []
        for period in self.periods:
            temp = factor_data[["factor", f"{period}D"]].dropna()
            ic = temp.groupby(temp.index.get_level_values("date")).apply(
                lambda x: x["factor"].corr(x[f"{period}D"])
            )
            ic_list.append(ic)
        ic_series = pd.concat(ic_list, axis=0)

        mean_ic = ic_series.mean()
        ir = ic_series.mean() / ic_series.std() if ic_series.std() != 0 else np.nan

        if len(ic_series.dropna()) > 1:
            _, p_value = stats.ttest_1samp(ic_series.dropna(), 0)
        else:
            p_value = np.nan
        p_score = 1 - p_value if not np.isnan(p_value) else 0

        mean_ret_by_q = factor_data.groupby(["date", "factor_quantile"]).mean()
        mean_ret_by_q = mean_ret_by_q.groupby("factor_quantile").mean()

        if mean_ret_by_q.index.isnull().all() or len(mean_ret_by_q) == 0:
            print(f"⚠️ Skipping {name} because quantile returns are empty.")
            with open(os.path.join(self.output_path, "error_log.txt"), "a") as f:
                f.write(f"{name}: quantile returns empty\n")
            return

        if self.quantiles >= 2:
            max_q = mean_ret_by_q.index.max()
            min_q = mean_ret_by_q.index.min()
            qr_diff = mean_ret_by_q.loc[max_q][f"{self.periods[0]}D"] - mean_ret_by_q.loc[min_q][f"{self.periods[0]}D"]
        else:
            qr_diff = np.nan

        factor_data = factor_data.sort_index()
        shifted_quantile = factor_data.groupby("asset")["factor_quantile"].shift(-self.periods[0])
        turnover_flags = (factor_data["factor_quantile"] != shifted_quantile)
        turnover_series = turnover_flags.groupby(level="date").mean()
        turnover = turnover_series.mean()

        score = 0.25 * mean_ic + 0.25 * ir + 0.2 * qr_diff + 0.2 * p_score - 0.2 * turnover

        self.summary.append({
            "factor": name,
            "mean_ic": mean_ic,
            "IR": ir,
            "QR_diff": qr_diff,
            "Turnover": turnover,
            "p_value": p_value,
            "p_score": p_score,
            "score": score
        })

    def run(self, start_date_str: str = None, end_date_str: str = None):
        print("\U0001F680 Starting Multi-Factor Analysis...")
        dummy_path = self.factor_paths[0]
        dummy_df = pd.read_csv(dummy_path, index_col=0, parse_dates=True)
        dummy_df.index.name = "date"
        dummy_long = dummy_df.reset_index().melt(id_vars=["date"], var_name="asset", value_name="factor")
        dummy_long = dummy_long.dropna().set_index(["date", "asset"]).sort_index()

        trading_dates = dummy_long.index.get_level_values("date").unique()

        if start_date_str and end_date_str:
            start_date = pd.to_datetime(start_date_str, format="%Y%m%d")
            end_date = pd.to_datetime(end_date_str, format="%Y%m%d")
            trading_dates = trading_dates[(trading_dates >= start_date) & (trading_dates <= end_date)]

        df_close = self.fetch_price_data(dummy_long)
        trading_dates = trading_dates.intersection(df_close.index)

        df_long = self.load_and_prepare_factors(trading_dates)

        grouped = df_long.groupby("factor_name")
        for name, group in grouped:
            self.analyze_single_factor(name, group, df_close)

        if self.summary:
            df_summary = pd.DataFrame(self.summary).sort_values(by="score", ascending=False)
            df_summary.to_csv(os.path.join(self.output_path, "factor_summary.csv"), index=False)

            passed_factors = df_summary[df_summary["p_value"] < 0.05]["factor"].tolist()
            passed_text = ", ".join(passed_factors)

            pvalue_df = pd.DataFrame({
                "factor": df_summary["factor"].tolist() + ["Passed Factors"],
                "p_value": df_summary["p_value"].tolist() + [passed_text]
            })
            pvalue_df.to_csv(os.path.join(self.output_path, "factor_pvalues.csv"), index=False)

            plt.figure(figsize=(12, len(df_summary) * 0.25))
            sns.barplot(data=df_summary, x="score", y="factor", palette="viridis")
            plt.title("Factor Scores", fontsize=14)
            plt.xlabel("Score", fontsize=12)
            plt.ylabel("Factor", fontsize=12)
            plt.xticks(fontsize=10)
            plt.yticks(fontsize=8)
            plt.grid(True, axis='x')
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_path, "factor_scores.png"))
        else:
            print("⚠️ No valid factors analyzed.")

        print("✅ Multi-factor analysis completed.")


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

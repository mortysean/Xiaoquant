import pandas as pd
import os
from utils.utils import project_path

def compute_factor_weights(summary_csv_path: str,
                           valid_factors: list) -> dict:
    """
    Compute factor weights based on IC * IR for valid factors.

    Args:
        summary_csv_path (str): Path to factor_summary.csv.
        valid_factors (list): List of factors to consider.

    Returns:
        dict: Mapping of {factor: weight}
    """
    df = pd.read_csv(summary_csv_path)
    df = df[df['factor'].isin(valid_factors)]

    df["ic_ir"] = df["mean_ic"].abs() * df["IR"]

    total_score = df["ic_ir"].sum()
    if total_score == 0:
        raise ValueError("❌ Total IC*IR score is zero. Cannot compute weights.")

    weights = (df.set_index("factor")["ic_ir"] / total_score).to_dict()

    print(f"✅ Computed weights for {len(weights)} factors.")
    return weights


def score_stocks(factor_root: str,
                 weights: dict,
                 start_date: str,
                 end_date: str) -> pd.DataFrame:
    """
    Compute stock scores based on multiple factors and their weights, with time filtering.
    """
    scores = []

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    for factor, weight in weights.items():
        factor_id = factor.replace("alpha", "").zfill(3)
        factor_file = f"alpha{factor_id}.csv"
        path = os.path.join(factor_root, factor_file)

        if not os.path.exists(path):
            print(f"⚠️ Skipping missing factor file: {path}")
            continue

        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index.name = "date"

        # ⛳ 筛选时间范围
        df = df.loc[(df.index >= start_date) & (df.index <= end_date)]

        df_long = df.reset_index().melt(id_vars=["date"], var_name="asset", value_name=factor)
        df_long.set_index(["date", "asset"], inplace=True)

        df_long = df_long * weight
        scores.append(df_long)

    if not scores:
        raise ValueError("❌ No valid factor data found to compute scores.")

    combined = pd.concat(scores, axis=1)
    combined["score"] = combined.sum(axis=1)

    result = combined[["score"]]
    print(f"✅ Computed multi-factor scores for {result.shape[0]} (date, asset) pairs.")
    return result

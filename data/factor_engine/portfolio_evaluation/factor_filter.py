import pandas as pd
import os
from utils.utils import project_path  # ✅ 添加这行

def filter_factors(summary_csv_path: str,
                   min_ic: float = 0.02,
                   min_ir: float = 0.2,
                   max_pvalue: float = 0.05) -> list:
    """
    Filter factors based on IC, IR, and p-value thresholds.

    Args:
        summary_csv_path (str): Path to factor_summary.csv.
        min_ic (float): Minimum absolute mean IC threshold.
        min_ir (float): Minimum IR threshold.
        max_pvalue (float): Maximum p-value threshold.

    Returns:
        list: List of factor names that pass the filter.
    """
    if not os.path.exists(summary_csv_path):
        raise FileNotFoundError(f"❌ factor_summary.csv not found at: {summary_csv_path}")

    df = pd.read_csv(summary_csv_path)

    required_columns = {"factor", "mean_ic", "IR", "p_value"}
    if not required_columns.issubset(df.columns):
        raise ValueError(f"❌ factor_summary.csv missing required columns: {required_columns}")

    filtered_df = df[
        (df["mean_ic"].abs() >= min_ic) &
        (df["IR"] >= min_ir) &
        (df["p_value"] <= max_pvalue)
    ]

    valid_factors = filtered_df["factor"].tolist()
    
    print(f"✅ {len(valid_factors)} factors passed the filter criteria.")
    return valid_factors


if __name__ == "__main__":
    # ✅ 直接用 project_path 拼接 summary_csv 路径
    summary_path = project_path(
        "data", "factor_engine", "factor_analysis", "analysis", "multi_factor", "Alphas101", "factor_summary.csv"
    )

    valid_factors = filter_factors(summary_csv_path=summary_path)
    print("Valid factors:", valid_factors)

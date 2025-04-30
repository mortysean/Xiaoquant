import pandas as pd
import os

def select_top_stocks(score_csv_path: str,
                      selection_date: str,
                      top_percent: float = 0.1,
                      output_path: str = None) -> pd.DataFrame:
    """
    Select top stocks based on multi-factor scores.

    Args:
        score_csv_path (str): Path to multi_factor_scores.csv.
        selection_date (str): Selection date, format 'YYYY-MM-DD'.
        top_percent (float): Top percentage of stocks to select.
        output_path (str): Path to save selected stocks (optional).

    Returns:
        pd.DataFrame: Selected stocks with columns [date, asset, score]
    """
    if not os.path.exists(score_csv_path):
        raise FileNotFoundError(f"❌ Score CSV not found at: {score_csv_path}")

    df = pd.read_csv(score_csv_path, parse_dates=["date"])
    df.set_index(["date", "asset"], inplace=True)

    target_date = pd.to_datetime(selection_date)

    # 🔁 自动回溯找最近有数据的日期
    available_dates = df.index.get_level_values("date").unique().sort_values(ascending=False)

    while target_date not in available_dates:
        target_date -= pd.Timedelta(days=1)
        if target_date < available_dates.min():
            raise ValueError(f"❌ No available scores even after backtracking. "
                             f"Earliest available date: {available_dates.min().strftime('%Y-%m-%d')}")

    print(f"✅ Using effective selection_date: {target_date.strftime('%Y-%m-%d')}")

    selected = df.loc[target_date].sort_values("score", ascending=False)
    top_n = max(1, int(len(selected) * top_percent))

    selected = selected.head(top_n).reset_index()  # 包含 date, asset, score 三列

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        selected.to_csv(output_path, index=False)
        print(f"✅ Selected stocks saved to {output_path}")

    return selected

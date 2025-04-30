import pandas as pd
import os

def build_portfolio(selected_stocks_path: str,
                    weight_mode: str = "equal",
                    output_path: str = None) -> pd.DataFrame:
    """
    Build a portfolio with assigned weights based on selected stocks.

    Args:
        selected_stocks_path (str): Path to selected_stocks.csv.
        weight_mode (str): "equal" or "score_weighted".
        output_path (str): Path to save the portfolio (optional).

    Returns:
        pd.DataFrame: Portfolio DataFrame with columns [asset, weight, score].
    """
    if not os.path.exists(selected_stocks_path):
        raise FileNotFoundError(f"❌ Selected stocks file not found at: {selected_stocks_path}")

    df = pd.read_csv(selected_stocks_path)

    if not {"asset", "score"}.issubset(df.columns):
        raise ValueError("❌ Selected stocks file must contain 'asset' and 'score' columns.")

    if weight_mode == "equal":
        df["weight"] = 1.0 / len(df)
    elif weight_mode == "score_weighted":
        total_score = df["score"].sum()
        if total_score == 0:
            raise ValueError("❌ Total score is zero. Cannot perform score-weighted allocation.")
        df["weight"] = df["score"] / total_score
    else:
        raise ValueError("❌ Invalid weight_mode. Must be 'equal' or 'score_weighted'.")

    portfolio = df[["asset", "weight", "score"]].copy()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        portfolio.to_csv(output_path, index=False)
        print(f"✅ Portfolio saved to {output_path}")

    return portfolio

 
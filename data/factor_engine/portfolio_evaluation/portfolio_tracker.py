import pandas as pd
import os
import matplotlib.pyplot as plt
from data.factor_engine.fetcher.clickhouse_fetcher import ClickHouseFetcher


def track_portfolio(portfolio_path: str,
                    start_date: str,
                    end_date: str,
                    output_path: str = None,
                    initial_capital: float = 1.0) -> pd.DataFrame:
    """
    Track portfolio net value using ClickHouse price data.

    Args:
        portfolio_path (str): CSV path with columns ['asset', 'weight'].
        start_date (str): Backtest start date (format: 'YYYYMMDD').
        end_date (str): Backtest end date (format: 'YYYYMMDD').
        output_path (str): Optional CSV path to save net value result.
        initial_capital (float): Starting portfolio value.

    Returns:
        pd.DataFrame: DataFrame with net value time series.
    """
    if not os.path.exists(portfolio_path):
        raise FileNotFoundError(f"❌ Portfolio file not found at: {portfolio_path}")

    portfolio = pd.read_csv(portfolio_path)
    if not {"asset", "weight"}.issubset(portfolio.columns):
        raise ValueError("❌ Portfolio CSV must contain 'asset' and 'weight' columns.")

    # Ensure proper date format and order
    if pd.to_datetime(start_date) > pd.to_datetime(end_date):
        print(f"⚠️ Swapping start and end dates: {start_date} > {end_date}")
        start_date, end_date = end_date, start_date

    start_date = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_date = pd.to_datetime(end_date).strftime("%Y-%m-%d")

    symbols = portfolio["asset"].tolist()
    weights = portfolio.set_index("asset")["weight"]

    print(f"✅ Portfolio Tracking Debug Info:\nStart Date: {start_date}, End Date: {end_date}")
    print(f"Assets: {symbols}")

    fetcher = ClickHouseFetcher()
    print(f"🧪 Fetching from ClickHouse: {symbols}, {start_date} -> {end_date}")
    df_price = fetcher.fetch(symbols=symbols, start=start_date, end=end_date, fields=["close"])
    print(f"📄 Fetch result shape: {df_price.shape}")
    print(df_price.head())

    if df_price.empty:
        raise ValueError("❌ No price data returned from ClickHouse.")

    df_close = df_price.pivot(index="date", columns="asset", values="close").sort_index()
    df_close = df_close.ffill().bfill()
    df_returns = df_close.pct_change().fillna(0)

    daily_returns = []
    dates = df_returns.index

    for date in dates:
        returns_today = df_returns.loc[date]
        available_assets = returns_today.dropna().index.intersection(weights.index)

        if len(available_assets) == 0:
            daily_returns.append(0)
            continue

        dynamic_weights = weights.loc[available_assets]
        dynamic_weights = dynamic_weights / dynamic_weights.sum()

        portfolio_return = (returns_today[available_assets] * dynamic_weights).sum()
        daily_returns.append(portfolio_return)

    net_value = (1 + pd.Series(daily_returns, index=dates)).cumprod() * initial_capital
    net_value_df = pd.DataFrame({"date": net_value.index, "net_value": net_value.values})

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        net_value_df.to_csv(output_path, index=False)
        print(f"✅ Net value curve saved: {output_path}")

    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(net_value_df["date"], net_value_df["net_value"], label="Net Value")
    plt.title("📈 Portfolio Net Value Curve")
    plt.xlabel("Date")
    plt.ylabel("Net Value")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    return net_value_df


def analyze_performance(net_value_df: pd.DataFrame) -> dict:
    """
    Analyze portfolio performance.

    Args:
        net_value_df (pd.DataFrame): DataFrame with ['date', 'net_value'].

    Returns:
        dict: Performance metrics.
    """
    returns = net_value_df["net_value"].pct_change().dropna()

    if returns.empty:
        raise ValueError("❌ No returns data available to analyze performance.")

    total_return = net_value_df["net_value"].iloc[-1] / net_value_df["net_value"].iloc[0] - 1
    annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
    annualized_volatility = returns.std() * (252 ** 0.5)
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility != 0 else float('nan')
    max_drawdown = ((net_value_df["net_value"].cummax() - net_value_df["net_value"]) / net_value_df["net_value"].cummax()).max()

    metrics = {
        "Total Return": total_return,
        "Annualized Return": annualized_return,
        "Annualized Volatility": annualized_volatility,
        "Sharpe Ratio": sharpe_ratio,
        "Max Drawdown": max_drawdown
    }

    print("\n📊 Portfolio Performance Metrics:")
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}")

    return metrics

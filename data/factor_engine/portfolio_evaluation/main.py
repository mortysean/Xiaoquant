import os
import warnings
import pandas as pd
from utils.utils import project_path

# Step 0: Global Config
START_DATE = "20241001"
END_DATE = "20250425"

SELECTION_DATE = "20250328"

FACTOR_LIB = "Alphas101"
TOP_PERCENT = 0.1
WEIGHT_MODE = "score_weighted"  # or "equal"

# Auto extract YEAR from START_DATE
YEAR = pd.to_datetime(START_DATE, format="%Y%m%d").year

# Path settings
summary_csv_path = project_path("data", "factor_engine", "factor_analysis", "analysis", "multi_factor", FACTOR_LIB, "factor_summary.csv")
factor_root = project_path("data", "factor_engine", "alphas", FACTOR_LIB, str(YEAR))
score_output_path = project_path("data", "factor_engine", "portfolio_evaluation", "backtest", "multi_factor_scores.csv")
selected_stocks_path = project_path("data", "factor_engine", "portfolio_evaluation", "backtest", "selected_stocks.csv")
portfolio_output_path = project_path("data", "factor_engine", "portfolio_evaluation", "backtest", "portfolio.csv")
net_value_output_path = project_path("data", "factor_engine", "portfolio_evaluation", "backtest", "net_value_curve.csv")
backtest_dir = project_path("data", "factor_engine", "portfolio_evaluation", "backtest")
os.makedirs(backtest_dir, exist_ok=True)

def get_next_trading_day(current_date: str) -> str:
    dt = pd.to_datetime(current_date, format="%Y%m%d")
    while dt.weekday() >= 5:
        dt += pd.Timedelta(days=1)
    return dt.strftime("%Y%m%d")

if __name__ == "__main__":
    warnings.filterwarnings("ignore")

    # === Step 0: Prepare T+1 backtest period
    BACKTEST_START_DATE = get_next_trading_day(
        (pd.to_datetime(SELECTION_DATE, format="%Y%m%d") + pd.Timedelta(days=1)).strftime("%Y%m%d")
    )
    print(f"📅 Effective backtest start date (T+1): {BACKTEST_START_DATE}")

    if pd.to_datetime(END_DATE) < pd.to_datetime(BACKTEST_START_DATE):
        print(f"⚠️ END_DATE {END_DATE} is earlier than BACKTEST_START_DATE {BACKTEST_START_DATE}, adjusting END_DATE...")
        END_DATE = (pd.to_datetime(BACKTEST_START_DATE) + pd.Timedelta(days=5)).strftime("%Y%m%d")

    # === Step 1: 筛选有效因子
    from data.factor_engine.portfolio_evaluation.factor_filter import filter_factors

    print("\n🔍 Step 1: Filtering valid factors...")
    valid_factors = filter_factors(summary_csv_path=summary_csv_path)
    print(f"✅ Valid factors: {valid_factors}\n")

    # === Step 2: 多因子打分
    from data.factor_engine.portfolio_evaluation.multi_factor_scorer import compute_factor_weights, score_stocks

    print("🧮 Step 2: Scoring stocks...")
    weights = compute_factor_weights(summary_csv_path=summary_csv_path, valid_factors=valid_factors)

    score_df = score_stocks(
        factor_root=factor_root,
        weights=weights,
        start_date=START_DATE,
        end_date=SELECTION_DATE
    )
    score_df.reset_index().to_csv(score_output_path, index=False)
    print(f"✅ Multi-factor scores saved: {score_output_path}\n")

    # === Step 3: 股票筛选
    from data.factor_engine.portfolio_evaluation.top_stocks_selector import select_top_stocks

    print("📋 Step 3: Selecting top stocks...")
    selected_df = select_top_stocks(
        score_csv_path=score_output_path,
        selection_date=pd.to_datetime(SELECTION_DATE, format="%Y%m%d").strftime("%Y-%m-%d"),
        top_percent=TOP_PERCENT,
        output_path=selected_stocks_path
    )
    print(f"✅ Selected stocks saved: {selected_stocks_path}\n")

    # === Step 4: 生成持仓
    from data.factor_engine.portfolio_evaluation.portfolio_builder import build_portfolio

    print("🛠 Step 4: Building portfolio...")
    portfolio_df = build_portfolio(
        selected_stocks_path=selected_stocks_path,
        weight_mode=WEIGHT_MODE,
        output_path=portfolio_output_path
    )
    print(f"✅ Portfolio saved: {portfolio_output_path}\n")

    # === Step 5: 回测
    from data.factor_engine.portfolio_evaluation.portfolio_tracker import track_portfolio, analyze_performance

    print("📈 Step 5: Tracking portfolio net value...")
    net_value_df = track_portfolio(
        portfolio_path=portfolio_output_path,
        start_date=BACKTEST_START_DATE,
        end_date=END_DATE,
        output_path=net_value_output_path
    )
    print(f"✅ Net value curve saved: {net_value_output_path}\n")

    # === Step 6: 绩效分析
    print("🧠 Step 6: Analyzing portfolio performance...")
    metrics = analyze_performance(net_value_df)
    print("✅ Evaluation finished.")

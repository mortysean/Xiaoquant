from .core.alphas101 import Alphas101
from .core.alphas191 import Alphas191
from .executor.factor_executor import ClassFactorExecutor
from exchanges.ashare_adapter import TushareAShareAdapter
import warnings

if __name__ == "__main__":
    adapter = TushareAShareAdapter()
    warnings.filterwarnings("ignore")

    # 获取沪深300成分股（确保该日期有数据）
    hs300_list = adapter.get_hs300_stocks("2022-01-04")

    # modify target_assets here
    target_assets = hs300_list
    print(hs300_list)


    # === 执行 Alphas101 因子 ===
    executor = ClassFactorExecutor(cls=Alphas101)
    executor.run_all(year="2025", list_assets=target_assets)

    # # === 如需切换到 Alphas191 因子，取消以下注释即可 ===
    # executor = ClassFactorExecutor(cls=Alphas191)
    # executor.run_all(year="2022", list_assets=hs300_list)

import os
import json
import traceback
from utils.utils import project_path  # ✅ 使用你提供的路径函数

class ClassFactorExecutor:
    def __init__(self, cls, save=True):
        self.cls = cls
        self.save = save

        # ✅ 使用 project_path 构建输出路径
        self.output_path = project_path("data", "factor_engine", "alphas", "error_log")
        os.makedirs(self.output_path, exist_ok=True)

    def run_single(self, factor_name, year="2022", list_assets=None, benchmark="000300.SH"):
        print(f"🚀 Running single factor '{factor_name}' for {self.cls.__name__} ...")
        try:
            return self.cls.generate_alpha_single(
                alpha_name=factor_name,
                year=year,
                list_assets=list_assets,
                benchmark=benchmark,
                need_save=self.save
            )
        except Exception as e:
            self._log_error(self.cls.__name__, factor_name, str(e))
            traceback.print_exc()
            return None

    def run_all(self, year="2022", list_assets=None, benchmark="000300.SH"):
        print(f"🚀 Running all factors for {self.cls.__name__} ...")
        try:
            self.cls.generate_alphas(year, list_assets, benchmark)
        except Exception as e:
            self._log_error(self.cls.__name__, "ALL", str(e))
            traceback.print_exc()

    def _log_error(self, lib, name, error_msg):
        log_dir = os.path.join(self.output_path, "logs")
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, f"{lib}_errors.json")

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                errors = json.load(f)
        else:
            errors = {}

        if name in errors:
            existing = errors[name]
            if isinstance(existing, list):
                existing.append(error_msg)
            else:
                errors[name] = [existing, error_msg]
        else:
            errors[name] = error_msg

        with open(path, "w", encoding="utf-8") as f:
            json.dump(errors, f, indent=4)

        print(f"🧾 Error logged at: {path}")

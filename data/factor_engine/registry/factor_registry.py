# factor_registry.py
import inspect

class ClassFactorRegistry:
    def __init__(self):
        self.factor_classes = {}

    def load_from_class(self, library_name, cls):
        """
        自动注册 class 中的 alphaXXX 方法
        """
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        factor_dict = {
            name: f"{cls.__name__}.{name}"
            for name, _ in methods
            if name.lower().startswith("alpha")
        }
        self.factor_classes[library_name] = {
            "class": cls,
            "factors": factor_dict
        }
        print(f"✅ Registered {len(factor_dict)} factors from {cls.__name__} as '{library_name}'")

    def list_factors(self, library_name):
        return list(self.factor_classes.get(library_name, {}).get("factors", {}).keys())

    def get_class(self, library_name):
        return self.factor_classes.get(library_name, {}).get("class")

    def get_method(self, library_name, factor_name):
        cls = self.get_class(library_name)
        if not cls:
            return None
        return getattr(cls, factor_name, None)
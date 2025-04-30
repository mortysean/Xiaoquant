import os


def project_path(*parts):
    """
    Construct an absolute path under the XiaoquantSystem root using the XIAOQUANT_ROOT environment variable.
    Defaults to current directory if the variable is not set.

    Example:
        project_path("data", "factor_engine", "alphas")
        -> /home/username/XiaoquantSystem/data/factor_engine/alphas
    """
    root = os.getenv("XIAOQUANT_ROOT", ".")
    return os.path.join(root, *parts)

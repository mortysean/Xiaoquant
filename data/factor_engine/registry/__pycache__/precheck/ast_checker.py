import json
import os
import re

# Define allowed node types based on your mappings
VALID_BINARY_OPS = set(BINARY_OPS := {"Addition", "Subtraction", "Multiplication", "Division", "Power"})
VALID_COMPARISON_OPS = set(COMPARISON_OPS := {"LessThan", "GreaterThan", "Equal", "NotEqual"})
VALID_CONDITIONAL_TYPES = set(CONDITIONAL_TYPES := {"Conditional"})
VALID_TERMINAL_TYPES = set(TERMINAL_TYPES := {"Variable", "Number"})
VALID_FUNCTION_NAMES = set(FUNCTION_MAP := {
    'rank', 'delta', 'delay', 'stddev', 'ts_sum', 'ts_min', 'ts_max', 'mean',
    'smean', 'ts_rank', 'ts_argmax', 'ts_argmin', 'wma', 'signedpower', 'sumif',
    'count', 'log', 'sin', 'cos', 'tan', 'abs', 'sign', 'sqrt', 'regbeta',
    'correlation', 'covariance', 'sma', 'sumac', 'decay_linear', 'where',
    # Added missing commonly used function names
    'sum', 'max', 'min', 'power', 'std', 'scale', 'or', 'and', 'not', 'indneutralize',
    'product', 'tsmax', 'tsmin', 'tsrank', 'corr', 'lowday', 'highday',
    'sequence', 'vol', 'ma', 'prod', 'adv30', 'adv20', 'adv10', 'adv5', 'decaylinear'
})

# Optional: function name aliases to normalize naming
FUNCTION_NAME_ALIASES = {
    'decaylinear': 'decay_linear',
    'indneutralize': 'indneutralize',  # normalize case
    'adv30': 'adv30',
    'adv20': 'adv20',
    'adv10': 'adv10',
    'adv5': 'adv5'
}

VALID_NODE_TYPES = (
    VALID_BINARY_OPS |
    VALID_COMPARISON_OPS |
    VALID_CONDITIONAL_TYPES |
    VALID_TERMINAL_TYPES |
    {"Function"}
)

def is_invalid_variable_node(node):
    name = node.get("name", "")
    return any(op in name for op in ["+", "-", "*", "/", "^", ">", "<", "=", "(", ")"])

def validate_ast_structure(node):
    if not isinstance(node, dict):
        raise ValueError("AST node is not a dict")

    if "type" not in node:
        raise ValueError("Missing 'type' in node")

    node_type = node["type"]

    if node_type not in VALID_NODE_TYPES:
        print(f"\u26a0\ufe0f  Warning: Unknown node type encountered: {node_type}, skipping structure check.")
        return

    if node_type in VALID_BINARY_OPS | VALID_COMPARISON_OPS:
        if "left" not in node or "right" not in node:
            raise ValueError(f"{node_type} missing 'left' or 'right'")
        validate_ast_structure(node["left"])
        validate_ast_structure(node["right"])

    elif node_type == "Function":
        if "name" not in node:
            raise ValueError("Function node missing 'name'")
        func_name = node["name"].lower()
        func_name = FUNCTION_NAME_ALIASES.get(func_name, func_name)
        if func_name not in VALID_FUNCTION_NAMES:
            raise ValueError(f"Unknown function name: {node['name']}")
        args = node.get("arguments", [])
        if not isinstance(args, list):
            raise ValueError("Function arguments must be a list")
        for arg in args:
            validate_ast_structure(arg)

    elif node_type == "Variable":
        if "name" not in node:
            raise ValueError("Variable node missing 'name'")

    elif node_type == "Number":
        if "value" not in node:
            raise ValueError("Number node missing 'value'")

    elif node_type in VALID_CONDITIONAL_TYPES:
        if not all(k in node for k in ("condition", "true_expr", "false_expr")):
            raise ValueError(f"{node_type} node missing condition / true_expr / false_expr")
        validate_ast_structure(node["condition"])
        validate_ast_structure(node["true_expr"])
        validate_ast_structure(node["false_expr"])

def validate_ast_semantics(node):
    node_type = node.get("type")

    if node_type == "Variable":
        if is_invalid_variable_node(node):
            raise ValueError(f"Invalid Variable name: {node['name']}")

    elif node_type in VALID_BINARY_OPS | VALID_COMPARISON_OPS:
        validate_ast_semantics(node["left"])
        validate_ast_semantics(node["right"])

    elif node_type == "Function":
        for arg in node["arguments"]:
            validate_ast_semantics(arg)

    elif node_type == "Number":
        pass

    elif node_type in VALID_CONDITIONAL_TYPES:
        validate_ast_semantics(node["condition"])
        validate_ast_semantics(node["true_expr"])
        validate_ast_semantics(node["false_expr"])

    else:
        print(f"\u26a0\ufe0f  Warning: Unknown node type during semantic check: {node_type}, skipping.")
        return

def extract_expected_factors(json_path):
    filename = os.path.basename(json_path)
    match = re.search(r'(alpha\d+)', filename)
    if not match:
        return set()
    base = match.group(1)
    count = 101 if base == 'alpha101' else 191 if base == 'alpha191' else 0
    return {f"{base[:-3]}_{i:03d}" for i in range(1, count + 1)}

def check_ast_file(json_file_path):
    with open(json_file_path, "r") as f:
        data = json.load(f)

    passed = 0
    failed = 0
    failed_log = {}

    for factor_name, content in data.items():
        if isinstance(content, dict) and "type" in content:
            ast = content
        elif isinstance(content, dict) and "ast" in content:
            ast = content.get("ast")
        else:
            ast = None

        if not ast or "type" not in ast:
            failed += 1
            failed_log[factor_name] = "Missing or invalid AST structure"
            continue

        try:
            validate_ast_structure(ast)
            validate_ast_semantics(ast)
            passed += 1
        except Exception as e:
            failed += 1
            failed_log[factor_name] = str(e)

    expected_factors = extract_expected_factors(json_file_path)
    actual_factors = set(data.keys())
    missing_factors = sorted(expected_factors - actual_factors)

    print(f"\n📊 Total Expected Factors: {len(expected_factors)}")
    print(f"📥 Total Loaded Factors: {len(data)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    if failed_log:
        print("\n❌ Failed Factors:")
        for name, reason in failed_log.items():
            print(f" - {name}: {reason}")

    if missing_factors:
        print("\n⚠️ Missing Factors (not in JSON):")
        for name in missing_factors:
            print(f" - {name}")

    return failed_log

def get_mock_context(lib_name):
    import pandas as pd
    import numpy as np
    idx = pd.date_range("2020-01-01", periods=100)
    mock = {
        "close": pd.Series(np.random.rand(100), index=idx),
        "open": pd.Series(np.random.rand(100), index=idx),
        "high": pd.Series(np.random.rand(100), index=idx),
        "low": pd.Series(np.random.rand(100), index=idx),
        "volume": pd.Series(np.random.rand(100), index=idx),
        "returns": pd.Series(np.random.randn(100), index=idx),
        "banchmarkindexclose": pd.Series(np.random.rand(100), index=idx),
        "banchmarkindexopen": pd.Series(np.random.rand(100), index=idx),
        "hd": pd.Series(np.random.rand(100), index=idx),
        "ld": pd.Series(np.random.rand(100), index=idx),
        "tr": pd.Series(np.random.rand(100), index=idx),
    }
    return mock

# Example entry point
if __name__ == "__main__":
    check_ast_file("/home/seanhuang/XiaoquantSystem/data/factor_engine/registry/factors/alpha101.json")

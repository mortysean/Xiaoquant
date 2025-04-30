import re

# Map Alpha function names to Python-style ts_function names
FUNC_MAP = {
    "SUM": "ts_sum",
    "MEAN": "mean",
    "STD": "stddev",
    "MAX": "ts_max",
    "MIN": "ts_min",
    "RANK": "rank",
    "CORR": "correlation",
    "COV": "covariance",
    "COUNT": "count",
    "DELAY": "delay",
    "DELTA": "delta",
    "SMA": "sma",
    "WMA": "wma",
    "DECAYLINEAR": "decaylinear",
    "TS_RANK": "ts_rank",
    "TS_ARGMAX": "ts_argmax",
    "TS_ARGMIN": "ts_argmin",
    "PRODUCT": "product",
    "ABS": "abs_",
    "SIGN": "sign_",
    "LOG": "log",
    "SIN": "sin",
    "COS": "cos",
    "TAN": "tan",
    "REGBETA": "regbeta",
    "SUMIF": "sumif",
    "SMEAN": "smean",
    "SUMAC": "sumac",
    "SIGNEDPOWER": "signedpower",
    "WHERE": "where"
}

OP_PRECEDENCE = {
    '==': 0, '!=': 0, '<': 0, '<=': 0, '>': 0, '>=': 0,
    '+': 1, '-': 1,
    '*': 2, '/': 2,
    '^': 3,
}

# --- Translate Alpha functions to Python-compatible string before parsing ---
def translate_expr(expr: str) -> str:
    expr = expr.strip()
    for alpha_func, py_func in FUNC_MAP.items():
        expr = re.sub(rf'\b{alpha_func}\b', py_func, expr, flags=re.IGNORECASE)
    return expr

# --- Tokenizer ---
def tokenize(expr: str):
    token_spec = [
        ('NUMBER',   r'\d+\.\d*|\.\d+|\d+'),
        ('NAME',     r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('OP',       r'(<=|>=|==|!=|<|>|[+\-*/^])'),
        ('LPAREN',   r'\('),
        ('RPAREN',   r'\)'),
        ('COMMA',    r','),
        ('QUESTION', r'\?'),
        ('COLON',    r':'),
        ('SKIP',     r'[ \t]+'),
        ('MISMATCH', r'.')
    ]
    tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_spec)
    tokens = []
    for mo in re.finditer(tok_regex, expr):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'SKIP':
            continue
        elif kind == 'MISMATCH':
            raise SyntaxError(f'Unexpected character {value}')
        tokens.append((kind, value))
    return tokens

# --- Recursive descent parser for token list ---
def parse_tokens(tokens):
    def parse_expression(min_prec=0):
        token = tokens.pop(0)
        if token[0] == 'NUMBER':
            node = float(token[1]) if '.' in token[1] else int(token[1])
        elif token[0] == 'NAME':
            if tokens and tokens[0][0] == 'LPAREN':
                func_name = token[1]
                tokens.pop(0)
                args = []
                while tokens and tokens[0][0] != 'RPAREN':
                    args.append(parse_expression())
                    if tokens and tokens[0][0] == 'COMMA':
                        tokens.pop(0)
                tokens.pop(0)
                node = {"op": func_name.lower()}
                if len(args) == 1:
                    node["arg"] = args[0]
                elif len(args) == 2:
                    node["arg"] = args[0]
                    node["params"] = {"n": args[1]}
                elif len(args) == 3:
                    node["arg"] = args[0]
                    node["params"] = {"t": args[1], "f": args[2]}
                else:
                    node["params"] = {"args": args}
            else:
                node = token[1].lower()
        elif token[0] == 'LPAREN':
            node = parse_expression()
            if tokens[0][0] != 'RPAREN':
                raise SyntaxError("Unclosed parenthesis")
            tokens.pop(0)
        else:
            raise SyntaxError(f"Unexpected token: {token}")

        while tokens and tokens[0][0] in ('OP', 'QUESTION'):
            if tokens[0][0] == 'QUESTION':
                tokens.pop(0)
                true_expr = parse_expression()
                if tokens[0][0] != 'COLON':
                    raise SyntaxError("Expected ':' in ternary")
                tokens.pop(0)
                false_expr = parse_expression()
                node = {
                    "op": "where",
                    "arg": node,
                    "params": {"t": true_expr, "f": false_expr}
                }
                break
            else:
                op = tokens.pop(0)[1]
                prec = OP_PRECEDENCE[op]
                if prec < min_prec:
                    tokens.insert(0, ('OP', op))
                    break
                rhs = parse_expression(prec + 1)
                node = {
                    "op": {
                        '+': 'add', '-': 'sub', '*': 'mul', '/': 'div', '^': 'pow',
                        '<': 'lt', '>': 'gt', '<=': 'le', '>=': 'ge', '==': 'eq', '!=': 'ne'
                    }[op],
                    "arg": node,
                    "params": {"rhs": rhs}
                }
        return node

    return parse_expression()

# --- Expression parser entry ---
def parse_expr(expr: str):
    expr = translate_expr(expr)
    tokens = tokenize(expr)
    return parse_tokens(tokens)

# --- AST Validator ---
def validate_ast(ast):
    if isinstance(ast, (str, int, float)):
        return True
    if isinstance(ast, dict):
        op = ast.get("op", "")
        if not isinstance(op, str) or not op.islower():
            print(f"❌ Invalid op (not lower): {op}")
            return False
        if not validate_ast(ast.get("arg", "")):
            return False
        params = ast.get("params", {})
        for v in params.values():
            if not validate_ast(v):
                return False
    return True

# --- Test Run ---
if __name__ == "__main__":
    expr = "(rank(ts_argmax(signedpower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)"
    print("🔢 Input:", expr)
    ast = parse_expr(expr)
    print("✅ AST:", ast)
    print("✅ Valid AST:", validate_ast(ast))

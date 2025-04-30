import os
import re
import json
from typing import Dict
from openai import OpenAI

# Initialize OpenAI client using API key from environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def validate_and_generate_ast(expression: str) -> Dict:
    """
    Validates a factor expression and generates an AST using GPT.

    Args:
        expression (str): The factor expression to validate.

    Returns:
        Dict: Contains original expression, validation result, error details, and parsed AST.
    """
    
    prompt = f"""
    You are a quantitative factor expression parser and validator.

    Your job is to:
    1. Validate the following factor expression for correct syntax.
    2. Convert it into an Abstract Syntax Tree (AST) that can be executed by a strict Python evaluator.
    3. Ensure the output AST conforms exactly to the following rules.

    📐 Supported AST Node Types (STRICT):

    1. Arithmetic Binary Operators:
    - "type": one of: "Addition", "Subtraction", "Multiplication", "Division", "Power"
    - Required fields: "left", "right" (both are AST nodes)

    2. Comparison Operators:
    - "type": one of: "LessThan", "GreaterThan", "Equal", "NotEqual"
    - Required fields: "left", "right"

    3. Conditional Expression:
    - "type": "Conditional"
    - Required fields: "condition", "true_expr", "false_expr"

    4. Function Call:
    - "type": "Function"
    - "name": one of (must be lowercase and from this list only):
        rank, delta, delay, stddev, ts_sum, ts_min, ts_max, mean, smean, ts_rank, ts_argmax, ts_argmin,
        wma, signedpower, sumif, count, log, sin, cos, tan, abs, sign, sqrt,
        regbeta, correlation, covariance, sma, sumac, decaylinear, where
    - "arguments": a list of AST nodes

    5. Variable:
    - "type": "Variable"
    - "name": must be a valid input symbol like "close", "open", "high", "low", "volume", "returns"
    - ❌ Do not embed expressions like "close/delay(close,1)" in variable names

    6. Number:
    - "type": "Number"
    - "value": must be an explicit float like 1.0, 2.5 (not 1 or 2.)

    🚫 Forbidden Constructs:
    - Do NOT use: BinaryOperator, binary, Arithmetic, Expr, or any symbolic operator types like "+", "<"
    - Do NOT invent function names or use TitleCase
    - Do NOT include any extra or unknown fields beyond what's listed above

    Now, process the following expression:

    ```txt
    {expression}
    Step 1: Report any syntax issues (if present).
    Step 2: Provide the corrected version of the expression.
    Step 3: Output the final AST in valid JSON format inside a single code block. """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        answer = response.choices[0].message.content

        print("\n=== Raw GPT Response ===\n")
        print(answer)

        def extract_field(pattern: str) -> str:
            match = re.search(pattern, answer)
            return match.group(1).strip() if match else ""

        def extract_ast_block() -> str:
            # 提取所有 markdown 代码块并尝试解析为 JSON
            blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", answer)
            for block in blocks:
                try:
                    json.loads(block)  # 尝试解析，成功就返回
                    return block.strip()
                except:
                    continue
            return ""


        def is_valid_ast(ast):
            return isinstance(ast, dict) and "type" in ast

        raw_ast = extract_ast_block()
        parsed_ast = {}
        is_valid = False

        if raw_ast:
            try:
                temp_ast = json.loads(raw_ast)
                if is_valid_ast(temp_ast):
                    parsed_ast = temp_ast
                    is_valid = True
            except Exception:
                pass


        return {
            "original_expression": expression,
            "is_valid": "Yes" if is_valid else "No",
            "error_description": extract_field(r"Error Description[:：]\s*(.*)"),
            "suggestion": extract_field(r"Suggested Fix[:：]\s*(.*)"),
            "error_type": extract_field(r"Error Type[:：]\s*(.*)"),
            "ast": parsed_ast
        }


    except Exception as e:
        return {
            "original_expression": expression,
            "is_valid": "Unknown",
            "error_description": f"GPT API error: {str(e)}",
            "suggestion": "",
            "error_type": "API Error",
            "ast": {}
        }

def ast_to_expression(ast: dict) -> str:
    ast_type = ast.get("type", "").lower()

    if ast_type == "function":
        args = [ast_to_expression(arg) for arg in ast.get("arguments", [])]
        return f'{ast.get("name", "UNKNOWN")}({", ".join(args)})'

    elif ast_type == "variable":
        return ast.get("name", "UNKNOWN")

    elif ast_type == "number":
        return str(ast.get("value", "0"))

    elif ast_type == "addition":
        return f'({ast_to_expression(ast.get("left", {}))} + {ast_to_expression(ast.get("right", {}))})'

    elif ast_type == "subtraction":
        return f'({ast_to_expression(ast.get("left", {}))} - {ast_to_expression(ast.get("right", {}))})'

    elif ast_type == "multiplication":
        return f'({ast_to_expression(ast.get("left", {}))} * {ast_to_expression(ast.get("right", {}))})'

    elif ast_type == "division":
        return f'({ast_to_expression(ast.get("left", {}))} / {ast_to_expression(ast.get("right", {}))})'

    elif ast_type == "power":
        return f'signedpower({ast_to_expression(ast.get("left", {}))}, {ast_to_expression(ast.get("right", {}))})'

    elif ast_type == "lessthan":
        return f'({ast_to_expression(ast.get("left", {}))} < {ast_to_expression(ast.get("right", {}))})'

    elif ast_type == "greaterthan":
        return f'({ast_to_expression(ast.get("left", {}))} > {ast_to_expression(ast.get("right", {}))})'

    elif ast_type == "equal":
        return f'({ast_to_expression(ast.get("left", {}))} == {ast_to_expression(ast.get("right", {}))})'

    elif ast_type == "notequal":
        return f'({ast_to_expression(ast.get("left", {}))} != {ast_to_expression(ast.get("right", {}))})'

    elif ast_type == "conditional" or ast_type == "ternary":
        return f'({ast_to_expression(ast.get("true_expr", {}))} if {ast_to_expression(ast.get("condition", {}))} else {ast_to_expression(ast.get("false_expr", {}))})'

    else:
        raise ValueError(f"Unknown AST node type in expression: {ast_type}")

if __name__ == "__main__":
    import pprint
    test_expr = "rank(ts_max(close 5)) - decay_linear(volume, 3)"
    result = validate_and_generate_ast(test_expr)

    print("=== Validation Result ===")
    pprint.pprint(result)

    if result["is_valid"] == "Yes" and result["ast"]:
        rebuilt = ast_to_expression(result["ast"])
        print("\n=== Reconstructed Expression ===")
        print(rebuilt)
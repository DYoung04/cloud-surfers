"""Calculator Lambda for the Cloud Surfers test environment.

Serves a minimal HTML form through API Gateway and evaluates basic
arithmetic. Each request should be logged in
"""

import json
import math
import operator
import time
from html import escape
from typing import Any, Callable

# Supported operations: query value -> (display symbol, implementation).
OPERATIONS: dict[str, tuple[str, Callable[[float, float], float]]] = {
    "add": ("+", operator.add),
    "subtract": ("-", operator.sub),
    "multiply": ("*", operator.mul),
    "divide": ("/", operator.truediv),
}

# the web page 
PAGE_TEMPLATE = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Cloud Surfers Calculator</title></head>
<body style="font-family: sans-serif; max-width: 400px; margin: 40px auto;">
  <h1>Cloud Surfers Calculator</h1>
  <form method="get">
    <input name="a" placeholder="First number" required>
    <select name="op">{options}</select>
    <input name="b" placeholder="Second number" required>
    <button type="submit">=</button>
  </form>
  <h2>{result}</h2>
</body>
</html>"""


# tells which operation, whether it worked, and who sent it (recording bascially)
def log_event(action: str, outcome: str, source_ip: str, **extra: Any) -> None:
    """Write a single structured log line to CloudWatch."""
    print(json.dumps({
        "ts": time.time(),
        "function": "calculator",
        "action": action,
        "outcome": outcome,
        "source_ip": source_ip,
        **extra,
    }))

# does the actual math
def calculate(params: dict[str, str]) -> float:
    """Evaluate the requested operation.

    Raises:
        ValueError: unknown operation, non-numeric input, or non-finite numbers.
        ZeroDivisionError: division by zero.
    """
    op = params.get("op")
    if op not in OPERATIONS:
        raise ValueError(f"unsupported operation: {op!r}")

    a = float(params.get("a", ""))
    b = float(params.get("b", ""))
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError("operands must be finite numbers")

    return OPERATIONS[op][1](a, b)

# actually builds the page, and sends it back 
def render(result: str = "") -> dict[str, Any]:
    """Build the API Gateway response containing the HTML page."""
    options = "".join(
        f'<option value="{name}">{symbol}</option>'
        for name, (symbol, _) in OPERATIONS.items()
    )
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": PAGE_TEMPLATE.format(options=options, result=escape(result)),
    }

# is the entry point, so AWS calls it on every request (bascially receiving the requestd)
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entry point invoked by API Gateway (GET /calc)."""
    params = event.get("queryStringParameters") or {}
    source_ip = event["requestContext"]["identity"]["sourceIp"]

    # First visit: no form submission yet, so just show the empty form.
    if not params:
        return render()

    op = params.get("op", "unknown")
    try:
        value = calculate(params)
    except (ValueError, ZeroDivisionError) as exc:
        log_event(op, "error", source_ip, error=type(exc).__name__)
        return render("Invalid input")

    log_event(op, "ok", source_ip)
    return render(f"Result: {value:g}")
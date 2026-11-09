
import argparse
from pathlib import Path
import base64
import csv
import json
import random
import re
import time
from collections import Counter, deque
from datetime import datetime, timezone

import boto3

REGION = "us-east-1"  # Change to your AWS Region
FUNCTION_NAME = "runtime-test-function"
parser = argparse.ArgumentParser(description="Invoke AWS Lambda 1000 times and record labeled measurements")
parser.add_argument("--experiment", choices=["baseline", "logistic_regression", "decision_tree"], default="logistic_regression",
                    help="Output grouping only; does not change the deployed model")
parser.add_argument("--output", type=Path, help="New CSV path; existing files are never overwritten")
args = parser.parse_args()
BASE = Path(__file__).resolve().parents[1]
run = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%S_%fZ")
OUTPUT_FILE = args.output or BASE / "data/raw" / args.experiment / run / "runtime_dataset.csv"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
if OUTPUT_FILE.exists():
    raise FileExistsError(f"Refusing to overwrite {OUTPUT_FILE}")

rng = random.Random(42)
lambda_client = boto3.client("lambda", region_name=REGION)


def generate_normal():
    words = ["hello", "order", "student", "report", "sample", "data"]
    size = rng.randint(5, 500)

    return {
        "action": "process",
        "value": " ".join(rng.choices(words, k=size)),
    }


def generate_injection():
    variants = [
        {"action": "process", "value": "<script>alert('x')</script>"},
        {"action": "process", "value": "' OR '1'='1"},
        {"action": "process", "value": "../../config"},
        {"action": "process", "value": "UNION SELECT secret"},
        {"action": "process", "value": "${malicious_input}"},
        {"action": "process", "value": "hello", "admin": True},
        {"action": "process", "value": None},
        ["malformed", "event"],
    ]
    return rng.choice(variants)


def generate_privilege_abuse():
    return {"action": "probe_protected_resource"}


events = []

for _ in range(600):
    events.append(("normal", 0, generate_normal()))

for _ in range(200):
    events.append(("event_injection", 1, generate_injection()))

for _ in range(200):
    events.append(("privilege_abuse", 1, generate_privilege_abuse()))

rng.shuffle(events)

fields = [
    "request_id",
    "timestamp",
    "duration_ms",
    "init_duration_ms",
    "cold_start",
    "invocation_count",
    "api_call_count",
    "access_denied_count",
    "error_count",
    "unexpected_target",
    "suspicious_input",
    "scenario_label",
    "binary_target",
]

duration_pattern = re.compile(r"(?<!Init )Duration:\s*([\d.]+)\s*ms")
init_pattern = re.compile(r"Init Duration:\s*([\d.]+)\s*ms")

recent_invocations = deque()
counts = Counter()


def invoke(event):
    response = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse",
        LogType="Tail",
        Payload=json.dumps(event).encode("utf-8"),
    )

    if response.get("FunctionError"):
        raise RuntimeError("Lambda execution failed")

    result = json.loads(response["Payload"].read())

    log_text = base64.b64decode(
        response["LogResult"]
    ).decode("utf-8", errors="replace")

    
    duration = None
    init_duration = None

    for line in log_text.splitlines():
        try:
            log = json.loads(line)
        except json.JSONDecodeError:
            continue

        if log.get("type") == "platform.report":
            metrics = log["record"]["metrics"]
            duration = metrics["durationMs"]
            init_duration = metrics.get("initDurationMs")
            break

    if duration is None:
        raise RuntimeError("Duration missing from Lambda REPORT log")

    return result, float(duration), (
        float(init_duration) if init_duration is not None else None
    )


    if not duration_match:
        print("\n=== LAMBDA LOG DEBUG ===")
        print(repr(log_text))
        print("========================\n")
        raise RuntimeError("Duration missing from Lambda REPORT log")

    return result, float(duration_match.group(1)), (
        float(init_match.group(1)) if init_match else None
    )


with open(OUTPUT_FILE, "x", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()

    for index, (label, target, event) in enumerate(events, 1):
        result, duration, init_duration = invoke(event)

        expected_statuses = {
            "normal": {"processed"},
            "event_injection": {
                "rejected_input",
                "invalid_input",
                "invalid_event",
            },
            "privilege_abuse": {"access_denied"},
        }

        if result["status"] not in expected_statuses[label]:
            raise RuntimeError(
                f"Unexpected result for {label}: {result['status']}"
            )

        now = time.time()
        recent_invocations.append(now)

        while recent_invocations and recent_invocations[0] < now - 60:
            recent_invocations.popleft()

        row = {
            "request_id": result["request_id"],
            "timestamp": datetime.fromtimestamp(
                now, timezone.utc
            ).isoformat(),
            "duration_ms": duration,
            "init_duration_ms": init_duration,
            "cold_start": int(init_duration is not None),
            "invocation_count": len(recent_invocations),
            "api_call_count": result["api_call_count"],
            "access_denied_count": result["access_denied_count"],
            "error_count": result["error_count"],
            "unexpected_target": result["unexpected_target"],
            "suspicious_input": result["suspicious_input"],
            "scenario_label": label,
            "binary_target": target,
        }

        writer.writerow(row)
        file.flush()
        counts[label] += 1

        if index % 100 == 0:
            print(f"Completed {index}/1000 invocations")

        time.sleep(rng.uniform(0.02, 0.15))

print("Dataset generated:", OUTPUT_FILE)
print("Scenario counts:", dict(counts))

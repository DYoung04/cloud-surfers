import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
import boto3

# ---- Settings (Darryl can tune these during testing) ----
STACK = "cloud-surfers"
REGION = "us-east-2"
LOOKBACK_MINUTES = int(os.environ.get("LOOKBACK_MINUTES", 24 * 60))
EXPECTED_SEARCH_KEYS = {"FilterExpression", "ExpressionAttributeNames", "ExpressionAttributeValues"}
MAX_SEARCH_RESULTS = 1
ERROR_LIMIT = 3
ALLOWED_ROLE_CALLS = {"CreateLogGroup", "CreateLogStream", "Decrypt"}

session = boto3.Session(region_name=REGION)
logs = session.client("logs")
trail = session.client("cloudtrail")
cfn = session.client("cloudformation")


def function_names():
    """Look up the real Lambda names created by the stack."""
    res = cfn.describe_stack_resources(StackName=STACK)["StackResources"]
    return {r["LogicalResourceId"]: r["PhysicalResourceId"]
            for r in res if r["ResourceType"] == "AWS::Lambda::Function"}


def read_logs(fn_name, start):
    """Pull the JSON log lines a function wrote since `start`."""
    events = []
    paginator = logs.get_paginator("filter_log_events")
    try:
        for page in paginator.paginate(logGroupName=f"/aws/lambda/{fn_name}",
                                       startTime=int(start.timestamp() * 1000)):
            for e in page["events"]:
                msg = e["message"].strip()
                if msg.startswith("{"):
                    try:
                        events.append(json.loads(msg))
                    except json.JSONDecodeError:
                        pass
    except logs.exceptions.ResourceNotFoundException:
        pass
    return events


def alert(alerts, severity, rule, detail):
    alerts.append({"severity": severity, "rule": rule, "detail": detail})


def check_injection(events, alerts):
    """Rule 1 + 3: odd search parameters, oversized results, error bursts."""
    errors = Counter()
    for e in events:
        if e.get("action") != "scan":
            continue
        if e.get("outcome") == "error":
            errors[e.get("source_ip")] += 1
            continue
        keys = set(e.get("keys", []))
        if keys != EXPECTED_SEARCH_KEYS:
            alert(alerts, "HIGH", "injection-unexpected-keys",
                  f"keys={sorted(keys)} results={e.get('result_count')} ip={e.get('source_ip')}")
        elif e.get("result_count", 0) > MAX_SEARCH_RESULTS:
            alert(alerts, "MEDIUM", "injection-large-result",
                  f"results={e.get('result_count')} ip={e.get('source_ip')}")
    for ip, n in errors.items():
        if n >= ERROR_LIMIT:
            alert(alerts, "MEDIUM", "error-burst", f"{n} failed searches from {ip}")


def check_privilege_logs(events, alerts):
    """Rule 2a: the function logged a table listing."""
    for e in events:
        if e.get("action") == "list_tables":
            alert(alerts, "HIGH", "privilege-debug-path", f"ip={e.get('source_ip')}")

def check_cloudtrail(start, alerts):
    """Rule 2b: a project role made an AWS API call outside its normal set."""
    paginator = trail.get_paginator("lookup_events")
    for page in paginator.paginate(StartTime=start, EndTime=datetime.now(timezone.utc)):
        for ev in page["Events"]:
            user = ev.get("Username", "")
            if user.startswith("cloud-surfers-Detector"):
                continue
            if user.startswith("cloud-surfers-") and ev["EventName"] not in ALLOWED_ROLE_CALLS:
                alert(alerts, "HIGH", "role-unexpected-api-call",
                      f"{user} called {ev['EventName']} at {ev['EventTime']}")


def main():
    start = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    fns = function_names()
    alerts = []
    check_injection(read_logs(fns["InjectionFunction"], start), alerts)
    check_privilege_logs(read_logs(fns["PrivilegeFunction"], start), alerts)
    check_cloudtrail(start, alerts)

    if not alerts:
        print("No anomalies found.")
        return
    for a in alerts:
        print(f"[{a['severity']}] {a['rule']}: {a['detail']}")
    print(f"\n{len(alerts)} alert(s)")


def handler(event, context):
    main()


if __name__ == "__main__":
    main()
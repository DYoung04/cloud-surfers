"""GET /report - privilege-abuse scenario.

The IAM role has broader permissions than it needs, and a leftover debug
flag uses them to list every table. That call shows up in CloudTrail.
"""

import json, os, time
import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
client = boto3.client("dynamodb")


def log_event(function, action, outcome, **extra):
    print(json.dumps({"ts": time.time(), "function": function,
                      "action": action, "outcome": outcome, **extra}))


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    ip = event["requestContext"]["identity"]["sourceIp"]

    # Vulnerable on purpose: debug flag lists tables, which this function
    # should never do.
    if params.get("debug") == "tables":
        names = client.list_tables()["TableNames"]
        log_event("privilege", "list_tables", "ok", source_ip=ip)
        return {"statusCode": 200, "body": json.dumps(names)}

    item = table.get_item(Key={"id": params.get("id", "1")}).get("Item")
    log_event("privilege", "get_item", "ok", source_ip=ip)
    return {"statusCode": 200, "body": json.dumps(item, default=str)}
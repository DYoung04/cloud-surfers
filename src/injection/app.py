import json, os, time
import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def log_event(function, action, outcome, **extra):
    print(json.dumps({"ts": time.time(), "function": function,
                      "action": action, "outcome": outcome, **extra}))

def handler(event, context):
    body = json.loads(event.get("body") or "{}")
    ip = event["requestContext"]["identity"]["sourceIp"]
    try:
        # VULNERABLE ON PURPOSE: request body becomes scan() arguments
        items = table.scan(**body).get("Items", [])
        log_event("injection", "scan", "ok", keys=list(body.keys()),
                  result_count=len(items), source_ip=ip)
        return {"statusCode": 200, "body": json.dumps(items, default=str)}
    except Exception as e:
        log_event("injection", "scan", "error", keys=list(body.keys()),
                  error=type(e).__name__, source_ip=ip)
        return {"statusCode": 400, "body": "bad request"}
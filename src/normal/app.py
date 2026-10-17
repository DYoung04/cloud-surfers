import json, os, time, uuid
import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def log_event(function, action, outcome, **extra):
    print(json.dumps({"ts": time.time(), "function": function,
                      "action": action, "outcome": outcome, **extra}))

def handler(event, context):
    body = json.loads(event.get("body") or "{}")
    item = {"id": str(body.get("id", uuid.uuid4())), "name": str(body.get("name", ""))}
    table.put_item(Item=item)
    log_event("normal", "put_item", "ok", keys=list(body.keys()),
              source_ip=event["requestContext"]["identity"]["sourceIp"])
    return {"statusCode": 200, "body": json.dumps(item)}
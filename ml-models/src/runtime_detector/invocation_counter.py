"""Shared rolling counter for this low-volume experiment, serialized by DynamoDB CAS.

One item per function holds the active 60-second window. No per-container count.
A production high-volume workload needs a partitioned telemetry service instead.
"""
import os
import time
import random


class InvocationCounter:
    def __init__(self, client, table, scope, clock=time.time, sleep=time.sleep):
        self.client, self.table, self.scope = client, table, scope
        self.clock, self.sleep = clock, sleep

    def record(self, request_id):
        if not request_id:
            raise ValueError("Missing invocation request ID")
        for attempt in range(8):
            item = self.client.get_item(
                TableName=self.table, Key={"scope": {"S": self.scope}},
                ConsistentRead=True).get("Item", {})
            now = int(self.clock() * 1000)
            entries = {k: int(v["N"]) for k, v in item.get("entries", {"M": {}})["M"].items()
                       if int(v["N"]) >= now - 60000}
            entries.setdefault(request_id, now)
            # Stay well below DynamoDB's 400 KB item limit; fail visibly, never guess.
            if len(entries) > 2000:
                raise RuntimeError("Counter capacity exceeded (2000 invocations per minute)")
            version = int(item.get("version", {"N": "0"})["N"])
            arguments = {
                "TableName": self.table,
                "Item": {"scope": {"S": self.scope}, "version": {"N": str(version + 1)},
                         "entries": {"M": {k: {"N": str(v)} for k, v in entries.items()}},
                         "expires_at": {"N": str(now // 1000 + 3600)}},
                "ConditionExpression": "#v = :v" if item else "attribute_not_exists(#v)",
                "ExpressionAttributeNames": {"#v": "version"},
            }
            if item:
                arguments["ExpressionAttributeValues"] = {":v": {"N": str(version)}}
            try:
                self.client.put_item(**arguments)
                return len(entries)
            except Exception as error:
                if getattr(error, "response", {}).get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                    raise
                self.sleep(random.uniform(0.005, 0.02) * (attempt + 1))
        raise RuntimeError("Counter contention retry limit exceeded")


_counter = None


def record_invocation(request_id, function_name):
    global _counter
    if _counter is None:
        import boto3
        from botocore.config import Config
        table = os.environ["INVOCATION_COUNTER_TABLE"]
        client = boto3.client("dynamodb", config=Config(
            connect_timeout=1, read_timeout=1, retries={"total_max_attempts": 2}))
        _counter = InvocationCounter(client, table, os.getenv("COUNTER_SCOPE", function_name))
    return _counter.record(request_id)

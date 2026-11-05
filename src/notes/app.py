"""Notes Lambda for the Cloud Surfers test environment.

Stores short notes and offers a search feature. The search path is
intentionally vulnerable to query (NoSQL) injection, mirroring the
existing /search scenario, so it produces attack telemetry the
detector recognizes. Each request emits one structured JSON log line.
"""

import json
import os
import time
import uuid

import boto3

table = boto3.resource("dynamodb").Table(os.environ["NOTES_TABLE"])


def log_event(action, outcome, source_ip, **extra):
    print(json.dumps({"ts": time.time(), "function": "notes",
                      "action": action, "outcome": outcome,
                      "source_ip": source_ip, **extra}))


def respond(status, body, content_type="application/json"):
    if content_type != "text/html":
        body = json.dumps(body, default=str)
    return {"statusCode": status, "headers": {"Content-Type": content_type}, "body": body}


PAGE = """<!doctype html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cloud Surfers Notes</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 480px; margin: 40px auto; padding: 0 16px; }
  textarea { width: 100%; padding: 10px; box-sizing: border-box; }
  button { padding: 10px 14px; border: 0; border-radius: 6px; background: #2f6fed; color: white; cursor: pointer; }
  li { background: #f2f4f8; padding: 10px; border-radius: 6px; margin: 6px 0; list-style: none; }
</style></head>
<body>
<h1>Cloud Surfers Notes</h1>
<textarea id="text" rows="3" placeholder="Write a note..."></textarea>
<p><button onclick="add()">Save note</button></p>
<ul id="list"></ul>
<script>
async function load() {
  const r = await fetch("notes");
  const items = await r.json();
  document.getElementById("list").innerHTML =
    items.map(n => "<li>" + n.text.replace(/</g,"&lt;") + "</li>").join("") || "<li>No notes yet.</li>";
}
async function add() {
  const t = document.getElementById("text");
  if (!t.value.trim()) return;
  await fetch("notes", { method: "POST", body: JSON.stringify({ text: t.value }) });
  t.value = ""; load();
}
load();
</script>
</body></html>"""


def handler(event, context):
    method = event.get("httpMethod")
    path = event.get("resource")
    ip = event["requestContext"]["identity"]["sourceIp"]

    if path == "/notes" and method == "GET" and not (event.get("queryStringParameters")):
        items = table.scan().get("Items", [])
        log_event("list", "ok", ip, result_count=len(items))
        return respond(200, items)

    if path == "/notes" and method == "POST":
        body = json.loads(event.get("body") or "{}")
        text = str(body.get("text", "")).strip()[:500]
        if not text:
            log_event("add", "error", ip, error="empty_text")
            return respond(400, {"error": "text is required"})
        item = {"id": uuid.uuid4().hex[:8], "text": text, "created": int(time.time())}
        table.put_item(Item=item)
        log_event("add", "ok", ip)
        return respond(201, item)

    if path == "/notes/search" and method == "POST":
        body = json.loads(event.get("body") or "{}")
        try:
            # VULNERABLE ON PURPOSE: request body becomes scan() arguments,
            # same injection class as the /search scenario.
            items = table.scan(**body).get("Items", [])
            log_event("scan", "ok", ip, keys=list(body.keys()), result_count=len(items))
            return respond(200, items)
        except Exception as e:
            log_event("scan", "error", ip, keys=list(body.keys()), error=type(e).__name__)
            return respond(400, {"error": "bad request"})

    if path == "/notesapp" and method == "GET":
        log_event("page", "ok", ip)
        return respond(200, PAGE, "text/html")

    log_event("unknown", "error", ip, method=method, path=path)
    return respond(404, {"error": "not found"})
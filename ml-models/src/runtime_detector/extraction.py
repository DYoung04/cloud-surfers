"""Extract logged fields using lambda_dataset.csv as the output schema.

Combines application messages and platform reports by request ID. Missing
fields stay empty. Labels come from runtime_dataset.csv's scenario_label,
joined by request_id; unmatched requests remain unlabeled.
Invocation counts use unique request IDs with platform.report timestamps in
the inclusive interval [completion time - 60 seconds, completion time].
Requests without a report timestamp have no derived invocation count.
Sensitive API call counts are set equal to API call counts.
Accepts a comma- or tab-separated reference header; output is standard CSV.
"""

import argparse
import csv
import json
from bisect import bisect_left, bisect_right
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


def json_object(value):
    if isinstance(value, dict):
        return value
    try:
        decoded = json.loads(value)
    except (ValueError, TypeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def extract(source, reference, output, runtime):
    if output.resolve() in {source.resolve(), reference.resolve(), runtime.resolve()}:
        raise ValueError("Output must not overwrite an input file")
    labels = {}
    with runtime.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not {"request_id", "scenario_label"}.issubset(reader.fieldnames or []):
            raise ValueError("Runtime CSV must contain request_id and scenario_label")
        for row in reader:
            request_id = row["request_id"]
            label = row["scenario_label"]
            if not request_id:
                continue
            if request_id in labels and labels[request_id] != label:
                raise ValueError(f"Conflicting labels for request_id {request_id}")
            labels[request_id] = label
    with reference.open(encoding="utf-8-sig", newline="") as file:
        header = file.readline()
    delimiter = "\t" if "\t" in header else ","
    fields = [field.strip() for field in next(csv.reader([header], delimiter=delimiter))]
    if not fields or any(not field for field in fields) or len(set(fields)) != len(fields):
        raise ValueError("Reference must contain a nonempty, unique field header")

    requests = {}
    completion_times = {}
    skipped = 0
    with source.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if "@message" not in (reader.fieldnames or []):
            raise ValueError("Source CSV must contain @message")
        for raw in reader:
            message = json_object(raw["@message"])
            record = json_object(message.get("record"))
            payload = json_object(message.get("message"))
            request_id = (payload.get("request_id") or message.get("request_id")
                          or record.get("requestId") or message.get("requestId")
                          or raw.get("@requestId"))
            if not request_id:
                skipped += 1
                continue
            row = requests.setdefault(request_id, {"request_id": request_id})
            for data in (message, payload):
                for field in fields:
                    if field != "request_id" and field in data:
                        row[field] = data[field]
            if message.get("type") == "platform.report":
                timestamp = message.get("time") or raw.get("@timestamp")
                if timestamp:
                    completed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if completed.tzinfo is None:
                        completed = completed.replace(tzinfo=timezone.utc)
                    # Duplicate reports still represent one invocation. Keep
                    # the latest completion, independent of CSV ordering.
                    completion_times[request_id] = max(
                        completed, completion_times.get(request_id, completed))
                metrics = json_object(record.get("metrics"))
                if "durationMs" in metrics:
                    row["duration_ms"] = metrics["durationMs"]

    times = sorted(completion_times.values())
    for request_id, row in requests.items():
        row["sensitive_api_call_count"] = row.get("api_call_count", "")
        completed = completion_times.get(request_id)
        row["invocation_count"] = (
            bisect_right(times, completed)
            - bisect_left(times, completed - timedelta(seconds=60))
            if completed is not None else ""
        )

    missing = Counter()
    label_counts = Counter()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in requests.values():
            row["label"] = labels.get(row["request_id"], "")
            label_counts[row["label"] or "unlabeled"] += 1
            writer.writerow(row)
            missing.update(field for field in fields if row.get(field) in (None, ""))
    print(f"Wrote {len(requests)} requests to {output}")
    print(f"Skipped {skipped} log records without a request ID")
    print(f"Derived 60-second invocation counts for {len(completion_times)} requests")
    print(f"Labels: {dict(label_counts)}")
    if missing:
        print("Blank fields (unavailable in source data): " + ", ".join(
            f"{field}={count}" for field, count in missing.items()))
    return len(requests)


def main():
    from .paths import PROJECT_ROOT
    base = PROJECT_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=base / "data/raw/baseline/run_001/log-analytics-results-2026-11-08.csv")
    parser.add_argument("--reference", type=Path, default=base / "docs/schemas/lambda_dataset.csv")
    parser.add_argument("--output", type=Path, default=base / "data/interim/lambda_dataset_extracted.csv")
    parser.add_argument("--runtime", type=Path, default=base / "data/raw/baseline/run_001/runtime_dataset.csv")
    args = parser.parse_args()
    try:
        extract(args.input, args.reference, args.output, args.runtime)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()

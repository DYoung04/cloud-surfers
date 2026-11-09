# Deployment after repository reorganization

The repository layout changed; the Lambda handler remains
`lambda_function.lambda_handler`. Existing ZIPs in `dist/` and the deployed AWS
function were not modified. Building a new ZIP copies the wrapper and application
to its root, inference modules into `runtime_detector/`, and the selected model
artifacts into `models/`. Research data, credentials, backups, and tests are excluded.

From the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/package_lambda.py --architecture x86_64
```

Defaults: `deployment/original_application.py` and `models/training_run_001/`.
Override with `--application PATH` or `--model-dir PATH`. Use `arm64` only for an
ARM Lambda. The build uses pinned Linux Python 3.14 wheels, checks package size,
and creates a fresh ZIP in `dist/`. It never deploys to AWS.

Back up the live function before uploading. Packages larger than 50 MiB compressed
need S3 upload in the Lambda's region. Total uncompressed package plus layers must
fit 250 MiB. Preserve application permissions and environment variables.

Required AWS configuration:

- Python 3.14; architecture matching the build.
- Handler: `lambda_function.lambda_handler`.
- `MODEL_NAME=logistic_regression` or `decision_tree`.
- `USE_SEPARATE_SCALER=true` for the saved Logistic Regression artifact.
- `INVOCATION_COUNTER_TABLE=runtime-detector-invocations`.
- `APPLICATION_HANDLER=original_application.lambda_handler`.
- `COUNTER_SCOPE=runtime-test-function` (or a consistent experiment scope).
- Existing `PROTECTED_BUCKET` and `PROTECTED_KEY` unchanged.

The DynamoDB counter table needs String partition key `scope`, no sort key,
on-demand capacity, and TTL on `expires_at`. The execution role needs GetItem and
PutItem on this table; see `counter-policy.json`. The function needs connectivity
to DynamoDB. The protected S3 probe should retain its existing denied-access behavior.

Smoke tests:

```json
{"action":"process","value":"hello world"}
```
```json
{"action":"process","value":"<script>alert('x')</script>"}
```
```json
{"action":"probe_protected_resource"}
```

Check CloudWatch for `runtime_detection`: expected binary predictions are 0, 1,
and 1, respectively. A `runtime_detection_error` with null prediction is a failed
detection, not normal behavior. Model predictions are not guaranteed. Keep memory,
timeout, traffic, and cold/warm reporting comparable when switching models.

References: [AWS Python packaging](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html).

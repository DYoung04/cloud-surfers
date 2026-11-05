# Cloud Surfers: Runtime Anomaly Detection for Serverless Applications

This repository contains the prototype for our CSC 452/552 research project on
detecting runtime attacks in serverless (AWS Lambda) applications. The goal is not a
new detection algorithm, but an experiment: we built a small, controlled AWS
environment, generated normal and malicious traffic against it, and tested whether a
lightweight Python detector that combines multiple AWS telemetry sources can reliably
catch two common attack classes, **event injection** and **privilege abuse**.

Everything described here is deployed as a single AWS SAM stack (`cloud-surfers`) in the
`us-east-2` region. The environment is already running, so testing mostly means sending
traffic to it and then checking what the detector reports.

## Design overview

A client sends HTTP requests to an API Gateway endpoint, which triggers Lambda
functions that read and write to a DynamoDB table. Three AWS services record what
happens: CloudWatch Logs captures what each function did, X-Ray traces the request
path, and CloudTrail records the AWS API calls each function's IAM role makes. A
separate detector Lambda reads the logs and CloudTrail events on a schedule and raises
alerts.

```
Client -> API Gateway -> Lambda functions -> DynamoDB
                               |
                               |-- CloudWatch Logs   (what each function did)
                               |-- X-Ray             (request traces)
                               '-- CloudTrail        (AWS API calls per IAM role)
                                            |
                                            '-> Detector Lambda (every 15 min) -> alerts
```

Using more than one telemetry source is the central idea of the project. Injection
attacks only appear in the function logs, because they never make an AWS API call.
Privilege abuse appears in CloudTrail, because it does. Catching privilege abuse in
both the logs and CloudTrail is what makes that detection stronger than a single-source
approach would be.

## Functions

| Function | Endpoint | Role in the experiment |
|---|---|---|
| Normal | `POST /items` | Honest baseline, scoped to least privilege |
| Injection | `POST /search` | Passes request input directly into a DynamoDB scan (vulnerable on purpose) |
| Privilege | `GET /report` | Granted broader IAM permissions than it needs; a debug flag lists DynamoDB tables |
| Notes | `GET /notesapp`, `/notes`, `POST /notes/search` | A realistic notes app carrying the same injection flaw |
| Calculator | `GET /calc` | Generates benign traffic; holds no database permissions |
| Detector | scheduled | Reads telemetry and reports anomalies |

The vulnerable functions are intentionally insecure so that we have repeatable attack
scenarios to measure against. They are not meant to represent good practice.

## Requirements

- AWS CLI and AWS SAM CLI, authenticated to the project account (`us-east-2`)
- Python 3.11
- A terminal for `curl` (Git Bash on Windows)

The only Python dependency is `boto3`, which the Lambda runtime already provides, so
there is nothing to install for deployment.

## Deploying

You only need to deploy if you change the code. From the project root:

```
sam build
sam deploy
```

The API base URL is printed under Outputs after a successful deploy:

```
https://3x8jnnknvl.execute-api.us-east-2.amazonaws.com/Prod
```

## Running the tests

Set the base URL once per terminal session:

```
API=https://3x8jnnknvl.execute-api.us-east-2.amazonaws.com/Prod
```

Generate normal traffic:

```
curl -X POST "$API/items" -d '{"id":"1","name":"apple"}'; echo
curl "$API/calc?a=5&op=add&b=3"; echo
```

Run the attacks:

```
curl -X POST "$API/search" -d '{}'; echo          # injection, dumps the whole table
curl -X POST "$API/notes/search" -d '{}'; echo     # injection through the notes app
curl "$API/report?debug=tables"; echo              # privilege abuse, lists the tables
```

To see the attacks without the detector (the baseline, traditional-monitoring case),
open the AWS console and read the raw telemetry yourself: CloudWatch for the function
logs, and CloudTrail Event history filtered to the `ListTables` event for the privilege
attack.

To see the detector catch them, invoke it directly:

```
sam remote invoke DetectorFunction --stack-name cloud-surfers
```

It prints one alert per detected attack and otherwise runs on its own every 15 minutes.
Note that it only looks back 30 minutes, so run it within a few minutes of the attacks
or it will report nothing.

## Detection rules

The detector lives in `detector/detector.py`. The constants at the top of the file
(the lookback window, the result-count threshold, the error limit, and the set of
allowed API calls) are the experimental variables we tune when measuring detection rate
against false positives.

| Rule | Condition | Source |
|---|---|---|
| `injection-unexpected-keys` | A search request carries unexpected parameters, such as an empty filter that returns the whole table | CloudWatch Logs |
| `error-burst` | Three or more failed searches from one IP, suggesting probing | CloudWatch Logs |
| `role-unexpected-api-call` | A function's role makes an AWS API call outside its normal set, such as `ListTables` | CloudTrail |

During development we found that Lambda's normal startup makes a `Decrypt` call that the
detector first flagged as suspicious. Adding it to the allowed set reduced our false
positives from three to zero, which is a small but concrete example of the
detection-versus-false-positive tradeoff the project is meant to study.

## Teardown

To remove every resource the stack created:

```
sam delete --stack-name cloud-surfers
```

## Repository layout

```
cloud-surfers/
├── template.yaml          # the full AWS stack, defined with SAM
├── detector/
│   └── detector.py        # the Python anomaly detector
└── src/
    ├── normal/app.py
    ├── injection/app.py
    ├── privilege/app.py
    ├── notes/app.py
    └── calculator/app.py
```

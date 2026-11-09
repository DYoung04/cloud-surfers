# Data dictionary

`request_id` (dataset), `invocation_id` (detector), and `record.requestId`
(platform REPORT) identify the same Lambda invocation. Join by these identifiers,
not row position. `@requestId` may be empty in the CSV export.

| Field | Definition |
| --- | --- |
| scenario_label / label | Ground-truth generated scenario: normal, event_injection, privilege_abuse |
| binary_target | Ground truth: normal=0, either attack scenario=1 |
| predicted_label | Model-predicted scenario; not the ground truth |
| prediction | Model binary output: normal=0, attack=1; null on detection failure |
| duration_ms in runtime CSV | Full Lambda platform REPORT duration |
| metrics.duration_ms in detector log | Application time measured before counter/inference; includes first-use application import |
| init_duration_ms | Initialization duration if present; blank is not a measured zero |
| cold_start | Whether the generator observed initialization duration |
| invocation_count in runtime CSV | Generator completions observed in the last 60 seconds |
| invocation_count in detector log | Shared DynamoDB registrations in the last 60 seconds |
| invocation_count in extracted baseline | Unique REPORT timestamps in the preceding inclusive 60-second window |
| api_call_count | Application API attempts; excludes detector counter calls |
| sensitive_api_call_count | Protected-resource probe attempts; equals API calls in this prototype |
| access_denied_count | Observed denied application API calls |
| error_count | Application-recorded input or processing errors |
| unexpected_target | Application flag for unexpected keys or protected-resource probing |
| suspicious_input | Application flag for matched suspicious input patterns |
| inference_ms | Feature preparation, scaling, and prediction time |
| detector_total_ms | Observer work including shared counter and inference; does not include model initialization |

The trained model schema has seven features. `sensitive_api_call_count` is
collected separately and is not an input to the current trained artifacts.
The reference schema in `schemas/lambda_dataset.csv` uses tabs despite its extension.

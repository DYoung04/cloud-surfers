# AWS Lambda runtime detector research

Experiments comparing Logistic Regression and Decision Tree classification of
normal, event-injection, and privilege-abuse invocations. The detector observes
application behavior and logs predictions without blocking the response.

## Project layout

| Location | Purpose |
| --- | --- |
| `data/raw/training/` | Preserved input dataset used for Phase 4 |
| `data/raw/baseline/run_001/` | Original runtime measurements and CloudWatch export |
| `data/raw/logistic_regression/run_001/` | Live LR measurements and corresponding CloudWatch export |
| `data/raw/decision_tree/` | Reserved for future live Decision Tree runs |
| `data/interim/` | Newly extracted or joined datasets |
| `data/processed/` | Existing 800/200 train/test split, preserved unchanged |
| `src/runtime_detector/` | Reusable inference, counter, extraction, training, validation, preprocessing |
| `scripts/` | Command-line entry points and Lambda packaging |
| `models/training_run_001/` | Existing trained models, scaler, feature list, metadata |
| `experiments/training/training_run_001/` | Existing offline test predictions and metrics |
| `experiments/{baseline,logistic_regression}/run_001/` | Live experiment provenance manifests |
| `deployment/` | Lambda wrapper, application handler, IAM policy, deployment guide |
| `docs/` | Methodology, feature definitions, schema, archived source, migration map |
| `reports/` | Figures, tables, and findings derived from experiments |
| `tests/` | Local tests; AWS calls mocked |
| `dist/` | Existing and future deployment ZIPs; not source code |
| `configs/` | Recorded training and experiment settings |
| `notebooks/` | Optional exploratory analysis |

Raw CSVs, processed split, existing model binaries, and existing result CSVs were
moved without changing their contents. `docs/reorganization.json` records old
paths, new paths, and pre-move hashes. Existing ZIPs remain unchanged in `dist/`.
Historical source backups are in `docs/archive/`. Local credential material is
kept in ignored `.local/` and must never be included in deployment artifacts.

## Local commands

Run from the repository root using the existing environment:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_dataset.py
.venv/bin/python scripts/extract_logs.py
.venv/bin/python scripts/train_models.py
.venv/bin/python scripts/package_lambda.py
```

`extract_logs.py` (also available as `extract_lambda_dataset.py`) reads the
baseline CloudWatch export, schema, and labels and writes
`data/interim/lambda_dataset_extracted.csv`. It refuses to overwrite that output.
Use `--input`, `--reference`, `--runtime`, and `--output` for other inputs.
This extractor creates the training-style schema; it is not a live-prediction
comparison tool.

Training uses the existing Phase 4 split and writes a **new** timestamped model
run and corresponding `experiments/training/` results. Existing runs are preserved.
Deployment defaults to `models/training_run_001`; select a different trained run
explicitly with `scripts/package_lambda.py --model-dir models/TRAINING_RUN`.
The recorded configurations in `configs/` describe the current experiment;
existing Python scripts remain the source of executable hyperparameters.

`preprocess.py` refuses to overwrite the existing split. Do not regenerate it
merely to reorganize files. Validation accepts `--input PATH`.

## AWS experiment commands (not run during reorganization)

```bash
.venv/bin/python scripts/generate_dataset.py --experiment logistic_regression
.venv/bin/python scripts/generate_dataset.py --experiment decision_tree
```

These invoke AWS Lambda 1,000 times and require credentials. `--experiment` selects
an output folder, **not** the deployed Lambda model. Set `MODEL_NAME` in AWS first.
Each command uses a new timestamped `data/raw/<experiment>/run_.../runtime_dataset.csv`.
An explicit `--output` must also be a new path. Export CloudWatch logs into that
same run folder and match by request ID. Preserve the scenario labels as ground truth.

See [deployment instructions](deployment/DEPLOYMENT.md),
[methodology](docs/methodology.md), and [data dictionary](docs/data_dictionary.md).

This organization adapts [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/)
and its [raw-data and reproducibility guidance](https://cookiecutter-data-science.drivendata.org/opinions/).

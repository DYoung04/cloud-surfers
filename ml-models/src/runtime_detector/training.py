"""Train Phase 5 models from the existing Phase 4 split without overwriting artifacts."""

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from .paths import PROJECT_ROOT

BASE = PROJECT_ROOT
FEATURES = [
    "duration_ms", "invocation_count", "api_call_count", "access_denied_count",
    "error_count", "unexpected_target", "suspicious_input",
]
LABELS = ["normal", "event_injection", "privilege_abuse"]


def load_split():
    processed = BASE / "data" / "processed"
    paths = [processed / name for name in
             ("X_train.csv", "X_test.csv", "y_train.csv", "y_test.csv")]
    if all(path.is_file() for path in paths):
        X_train, X_test, train_labels, test_labels = [pd.read_csv(p) for p in paths]
        y_train, y_test = train_labels["label"], test_labels["label"]
    else:
        train = pd.read_csv(BASE / "data" / "train.csv")
        test = pd.read_csv(BASE / "data" / "test.csv")
        X_train, X_test = train[FEATURES], test[FEATURES]
        y_train, y_test = train["label"], test["label"]
    X_train, X_test = X_train[FEATURES], X_test[FEATURES]
    if (len(X_train), len(y_train), len(X_test), len(y_test)) != (800, 800, 200, 200):
        raise ValueError("Expected 800 aligned training rows and 200 aligned test rows")
    for X, y in ((X_train, y_train), (X_test, y_test)):
        if not np.isfinite(X.to_numpy(dtype=float)).all():
            raise ValueError("Features must be finite numeric values")
        if y.isna().any() or set(y) != set(LABELS):
            raise ValueError(f"Each split must contain these labels: {LABELS}")
    return X_train, X_test, y_train, y_test


def output_directories():
    models, results = BASE / "models", BASE / "experiments" / "training"
    # Keep all existing outputs intact; use paired run folders if either is populated.
    if any(path.exists() and any(path.iterdir()) for path in (models, results)):
        run = datetime.now(timezone.utc).strftime("training_run_%Y%m%dT%H%M%S_%fZ")
        models, results = models / run, results / run
    models.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    return models, results


def main():
    X_train, X_test, y_train, y_test = load_split()
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    lr_model = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    lr_model.fit(X_train_scaled, y_train)
    dt_model = DecisionTreeClassifier(max_depth=5, min_samples_leaf=5, random_state=42)
    dt_model.fit(X_train, y_train)
    predictions = {
        "logistic_regression": lr_model.predict(X_test_scaled),
        "decision_tree": dt_model.predict(X_test),
    }
    models, results = output_directories()
    for name, artifact in (("logistic_regression", lr_model), ("decision_tree", dt_model),
                           ("scaler", scaler), ("feature_names", FEATURES)):
        joblib.dump(artifact, models / f"{name}.joblib")
    pd.DataFrame({"actual": y_test.to_numpy(), **predictions}).to_csv(
        results / "predictions.csv", index=False)
    for name, predicted in predictions.items():
        print(f"\n{name}")
        print(classification_report(y_test, predicted, labels=LABELS, zero_division=0))
        report = classification_report(y_test, predicted, labels=LABELS,
                                       output_dict=True, zero_division=0)
        pd.DataFrame(report).transpose().to_csv(results / f"{name}_metrics.csv")
        matrix = pd.DataFrame(confusion_matrix(y_test, predicted, labels=LABELS),
                              index=LABELS, columns=LABELS)
        matrix.index.name = "actual"
        matrix.columns.name = "predicted"
        matrix.to_csv(results / f"{name}_confusion_matrix.csv")
        print(matrix)
    metadata = {"training_rows": len(X_train), "testing_rows": len(X_test),
                "features": FEATURES, "labels": LABELS,
                "training_class_counts": y_train.value_counts().to_dict(),
                "testing_class_counts": y_test.value_counts().to_dict()}
    (results / "training_summary.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (models / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    # Verify saved artifacts reproduce the predictions with the saved feature order.
    saved_features = joblib.load(models / "feature_names.joblib")
    saved_scaler = joblib.load(models / "scaler.joblib")
    for name, data in (("logistic_regression", saved_scaler.transform(X_test[saved_features])),
                       ("decision_tree", X_test[saved_features])):
        restored = joblib.load(models / f"{name}.joblib")
        if not np.array_equal(restored.predict(data), predictions[name]):
            raise RuntimeError(f"Saved {name} predictions differ")
    print(f"\nModels: {models}\nResults: {results}")
    print("Verified saved models reproduce all 200 test predictions.")


if __name__ == "__main__":
    main()

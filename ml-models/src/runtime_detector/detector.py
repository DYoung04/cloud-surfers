"""Warm-reused inference using the exact Phase 5 feature schema and scaler."""
import math
import os
import time
from pathlib import Path

MODEL_NAME = os.getenv("MODEL_NAME", "logistic_regression")
# Repository models are versioned; the Lambda build places the selected run at /var/task/models.
_repository_models = Path(__file__).resolve().parents[2] / "models" / "training_run_001"
_packaged_models = Path(__file__).resolve().parents[1] / "models"
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(
    _repository_models if _repository_models.is_dir() else _packaged_models)))
_model = _scaler = _features = None
_load_error = None


def _load():
    global _model, _scaler, _features
    import joblib
    if MODEL_NAME not in {"logistic_regression", "decision_tree"}:
        raise ValueError("Unsupported MODEL_NAME")
    _features = joblib.load(MODEL_DIR / "feature_names.joblib")
    _model = joblib.load(MODEL_DIR / f"{MODEL_NAME}.joblib")
    if _model.n_features_in_ != len(_features) or (
        hasattr(_model, "feature_names_in_") and list(_model.feature_names_in_) != _features
    ):
        raise ValueError("Model feature names do not match saved schema")
    if MODEL_NAME == "logistic_regression":
        # Phase 5 saved a separate scaler. It is mandatory for these artifacts.
        if os.getenv("USE_SEPARATE_SCALER", "true").lower() != "true":
            raise ValueError("This Logistic Regression artifact requires USE_SEPARATE_SCALER=true")
        _scaler = joblib.load(MODEL_DIR / "scaler.joblib")
        if list(_scaler.feature_names_in_) != _features:
            raise ValueError("Scaler feature names do not match saved schema")


# Loading failures are deferred to detect so application responses still succeed.
try:
    _load()
except Exception as error:
    _load_error = error


def detect(metrics):
    if _load_error is not None:
        raise RuntimeError("Detector initialization failed") from _load_error
    import pandas as pd
    started = time.perf_counter()
    values = [float(metrics[name]) for name in _features]
    if not all(math.isfinite(value) and value >= 0 for value in values):
        raise ValueError("Telemetry must be finite and nonnegative")
    frame = pd.DataFrame([values], columns=_features)
    inputs = _scaler.transform(frame) if _scaler is not None else frame
    label = str(_model.predict(inputs)[0])
    if label not in {"normal", "event_injection", "privilege_abuse"}:
        raise ValueError("Unexpected predicted label")
    return {"prediction": int(label != "normal"), "predicted_label": label,
            "model_name": MODEL_NAME,
            "inference_ms": (time.perf_counter() - started) * 1000}

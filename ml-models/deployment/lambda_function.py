"""Observer wrapper around the existing, unchanged Lambda application module.

Package the original handler as original_application.py. It may return the
existing response dictionary containing telemetry, or (response, telemetry).
"""
import importlib
import json
import logging
import os
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Keep detector initialization failures from preventing application execution.
_detector_error = None
try:
    from runtime_detector.detector import detect, MODEL_NAME
except Exception as error:
    _detector_error = error
    MODEL_NAME = os.getenv("MODEL_NAME", "logistic_regression")

from runtime_detector.invocation_counter import record_invocation

_application = None
TELEMETRY_FIELDS = ("api_call_count", "access_denied_count", "error_count",
                    "unexpected_target", "suspicious_input", "sensitive_api_call_count")


def application_handler(event, context):
    global _application
    if _application is None:
        target = os.getenv("APPLICATION_HANDLER", "original_application.lambda_handler")
        module_name, function_name = target.rsplit(".", 1)
        if module_name == "lambda_function":
            raise ValueError("APPLICATION_HANDLER must not refer to the wrapper")
        _application = getattr(importlib.import_module(module_name), function_name)
    # Preserve the existing response exactly. Telemetry extraction happens inside
    # the observer's error boundary, so missing fields do not break the application.
    return _application(event, context)


def lambda_handler(event, context):
    started = time.perf_counter()
    output = application_handler(event, context)
    duration_ms = (time.perf_counter() - started) * 1000
    if isinstance(output, tuple) and len(output) == 2:
        response, telemetry = output
    else:
        response = telemetry = output
    detector_started = time.perf_counter()
    try:
        if _detector_error is not None:
            raise RuntimeError("Detector import failed") from _detector_error
        metrics = {name: telemetry[name] for name in TELEMETRY_FIELDS}
        metrics["duration_ms"] = duration_ms
        metrics["invocation_count"] = record_invocation(
            context.aws_request_id, context.function_name)
        result = detect(metrics)
        logger.info(json.dumps({"event_type": "runtime_detection",
                               "invocation_id": context.aws_request_id,
                               **result, "metrics": metrics,
                               "detector_total_ms": (time.perf_counter() - detector_started) * 1000}))
    except Exception as error:
        logger.error(json.dumps({"event_type": "runtime_detection_error",
                                "invocation_id": context.aws_request_id,
                                "model_name": MODEL_NAME, "prediction": None,
                                "error_type": type(error).__name__,
                                "error": str(error),
                                "detector_total_ms": (time.perf_counter() - detector_started) * 1000}))
    return response

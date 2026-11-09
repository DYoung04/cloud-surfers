"""Verify the reorganized source builds a self-contained Lambda payload."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_payload_imports_outside_repository(self):
        spec = importlib.util.spec_from_file_location('package_lambda', ROOT / 'scripts/package_lambda.py')
        packaging = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(packaging)
        with tempfile.TemporaryDirectory() as folder:
            build = Path(folder)
            packaging.stage_payload(build, ROOT / 'deployment/original_application.py',
                                    ROOT / 'models/training_run_001')
            self.assertEqual({p.name for p in build.iterdir()},
                             {'lambda_function.py', 'original_application.py', 'runtime_detector', 'models'})
            environment = os.environ.copy()
            environment.pop('MODEL_DIR', None)
            environment.pop('PYTHONPATH', None)
            environment['USE_SEPARATE_SCALER'] = 'true'
            for model in ('logistic_regression', 'decision_tree'):
                environment['MODEL_NAME'] = model
                subprocess.run([sys.executable, '-c', '''
from pathlib import Path
from runtime_detector import detector
import lambda_function
assert detector._load_error is None, repr(detector._load_error)
assert detector.MODEL_DIR.resolve() == (Path.cwd() / "models").resolve()
assert lambda_function._detector_error is None
assert detector.detect(dict(duration_ms=2, invocation_count=1, api_call_count=0,
    access_denied_count=0, error_count=0, unexpected_target=0, suspicious_input=0))["prediction"] == 0
'''], cwd=build, env=environment, check=True, capture_output=True, text=True)

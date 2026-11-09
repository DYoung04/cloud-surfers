import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "deployment"))
import copy
import csv
import importlib
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from runtime_detector.invocation_counter import InvocationCounter

BASE = Path(__file__).resolve().parents[1]


class CounterClient:
    def __init__(self):
        self.item = {}
        self.conflict = False

    def get_item(self, **kwargs):
        assert kwargs['ConsistentRead'] is True
        return {'Item': copy.deepcopy(self.item)}

    def put_item(self, **kwargs):
        if self.conflict:
            self.conflict = False
            error = RuntimeError('conflict')
            error.response = {'Error': {'Code': 'ConditionalCheckFailedException'}}
            raise error
        self.item = kwargs['Item']


class RuntimeTests(unittest.TestCase):
    def test_scaler_configuration_failure_is_reported(self):
        from runtime_detector import detector
        with patch.dict(os.environ, {'MODEL_NAME': 'logistic_regression', 'USE_SEPARATE_SCALER': 'false'}):
            importlib.reload(detector)
            with self.assertRaisesRegex(RuntimeError, 'initialization failed'):
                detector.detect({})
        importlib.reload(detector)

    def test_saved_predictions_for_both_models(self):
        from runtime_detector import detector
        with (BASE / 'data/processed/X_test.csv').open() as file:
            rows = list(csv.DictReader(file))
        with (BASE / 'experiments/training/training_run_001/predictions.csv').open() as file:
            expected = list(csv.DictReader(file))
        for name in ('logistic_regression', 'decision_tree'):
            with patch.dict(os.environ, {'MODEL_NAME': name, 'USE_SEPARATE_SCALER': 'true'}):
                importlib.reload(detector)
                for row, reference in zip(rows, expected):
                    result = detector.detect(row)
                    self.assertEqual(result['predicted_label'], reference[name])
                    self.assertEqual(result['prediction'], int(reference[name] != 'normal'))
                    self.assertGreaterEqual(result['inference_ms'], 0)
                with self.assertRaises(KeyError):
                    detector.detect({})
                with self.assertRaises(ValueError):
                    detector.detect({**rows[0], 'duration_ms': np.nan})
        importlib.reload(detector)

    def test_counter_window_deduplication_and_retry(self):
        client = CounterClient()
        clock = [100.0]
        counter = InvocationCounter(client, 'table', 'function', clock=lambda: clock[0], sleep=lambda _: None)
        self.assertEqual(counter.record('a'), 1)
        self.assertEqual(counter.record('a'), 1)
        # A separate execution environment shares the same backing store.
        other = InvocationCounter(client, 'table', 'function', clock=lambda: clock[0], sleep=lambda _: None)
        clock[0] = 160.0
        client.conflict = True
        self.assertEqual(other.record('b'), 2)
        clock[0] = 160.001
        self.assertEqual(counter.record('c'), 2)

    def test_wrapper_preserves_response_and_logs_errors(self):
        import lambda_function as wrapper
        context = SimpleNamespace(aws_request_id='test', function_name='runtime-test-function')
        response = dict(api_call_count=1, sensitive_api_call_count=1, access_denied_count=1,
                        error_count=0, unexpected_target=1, suspicious_input=0, status='access_denied')
        with patch.object(wrapper, '_application', return_value=response), \
             patch.object(wrapper, 'record_invocation', return_value=12), \
             patch.object(wrapper, 'detect', return_value={'prediction': 1, 'model_name': 'decision_tree'}) as detect:
            with self.assertLogs(level='INFO') as logs:
                self.assertIs(wrapper.lambda_handler({}, context), response)
            self.assertEqual(detect.call_args.args[0]['invocation_count'], 12)
            self.assertIn('runtime_detection', logs.output[0])
        with patch.object(wrapper, '_application', return_value=response), \
             patch.object(wrapper, 'record_invocation', side_effect=RuntimeError('counter unavailable')):
            with self.assertLogs(level='ERROR') as logs:
                self.assertIs(wrapper.lambda_handler({}, context), response)
            self.assertIn('"prediction": null', logs.output[0])
        with patch.object(wrapper, '_application', return_value={'status': 'original'}):
            with self.assertLogs(level='ERROR'):
                self.assertEqual(wrapper.lambda_handler({}, context), {'status': 'original'})
        with patch.object(wrapper, '_application', return_value=({'body': 'unchanged'}, response)), \
             patch.object(wrapper, 'record_invocation', return_value=1), \
             patch.object(wrapper, 'detect', side_effect=RuntimeError('inference failed')):
            with self.assertLogs(level='ERROR'):
                self.assertEqual(wrapper.lambda_handler({}, context), {'body': 'unchanged'})
        with patch.object(wrapper, '_application', side_effect=ValueError('application failure')):
            with self.assertRaisesRegex(ValueError, 'application failure'):
                wrapper.lambda_handler({}, context)


if __name__ == '__main__':
    unittest.main()

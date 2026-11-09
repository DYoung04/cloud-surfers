import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "deployment"))
import importlib
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError


class ApplicationTests(unittest.TestCase):
    def test_original_responses_and_sensitive_counts(self):
        s3 = Mock()
        s3.head_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}}, 'HeadObject')
        with patch('boto3.client', return_value=s3):
            module = importlib.import_module('original_application')
            importlib.reload(module)
            original = {}
            path = Path(__file__).resolve().parents[1] / 'docs/archive/original_application.py.original'
            exec(compile(path.read_text(), str(path), 'exec'), original)
        context = SimpleNamespace(aws_request_id='local-test', function_name='runtime-test-function')
        events = [
            {'action': 'process', 'value': 'hello'},
            {'action': 'process', 'value': "<script>alert('x')</script>"},
            {'action': 'probe_protected_resource'},
            ['malformed'], {'action': 'process', 'value': None},
            {'action': 'process', 'value': 'hello', 'admin': True},
        ]
        with patch.dict(os.environ, {'PROTECTED_BUCKET': 'test-bucket', 'PROTECTED_KEY': 'test-key'}):
            for event in events:
                expected = original['lambda_handler'](event, context)
                response, metrics = module.lambda_handler(event, context)
                self.assertEqual({k: v for k, v in expected.items() if k != 'processing_ms'},
                                 {k: v for k, v in response.items() if k != 'processing_ms'})
                self.assertEqual(metrics['sensitive_api_call_count'], metrics['api_call_count'])
            import lambda_function as wrapper
            with patch.object(wrapper, '_application', module.lambda_handler), \
                 patch.object(wrapper, 'record_invocation', return_value=1):
                with self.assertLogs(level='INFO') as logs:
                    response = wrapper.lambda_handler(events[0], context)
                self.assertEqual(response['status'], 'processed')
                self.assertTrue(any('"event_type": "runtime_detection"' in line for line in logs.output))
                self.assertFalse(any('runtime_detection_error' in line for line in logs.output))

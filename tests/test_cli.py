import contextlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run_bench


class CLI(unittest.TestCase):
    def invoke(self, *args, env=None):
        return subprocess.run(
            [sys.executable, str(ROOT / 'run_bench.py'), *args],
            capture_output=True, text=True, cwd=self.tmp,
            env={**os.environ, 'OPENAI_API_KEY': '', **(env or {})},
        )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)

    def test_help_describes_all_configuration_flags(self):
        result = self.invoke('--help')
        self.assertEqual(result.returncode, 0)
        for flag in ('-config', '--api-key', '--request-timeout', '--exec-timeout',
                     '--extra-body', '--no-stream'):
            self.assertIn(flag, result.stdout)

    def test_bad_config_and_values_are_usage_errors(self):
        path = self.tmp / 'bad.json'
        for content in ('{', '[]', '{"concurrency":0}', '{"stream":"false"}',
                        '{"max_token":42}', '{"extra_body":[]}', '{"temperature":NaN}',
                        '{"extra_body":{"model":"unexpected-model"}}',
                        '{"extra_body":{"temperature":1}}',
                        '{"extra_body":{"max_tokens":1}}'):
            path.write_text(content)
            with self.subTest(content=content):
                result = self.invoke('--config', str(path), '--list')
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('Traceback', result.stderr)
        for args in (('--config', str(self.tmp / 'missing.json')),
                     ('--request-timeout', '0'), ('--base-url', 'ftp://host'),
                     ('--extra-body', '[]'), ('--limit', '-1')):
            with self.subTest(args=args):
                self.assertEqual(self.invoke(*args, '--list').returncode, 2)

    def test_environment_key_and_stream_configuration(self):
        path = self.tmp / 'config.json'
        path.write_text('{"stream":true,"concurrency":4}')
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': 'environment-key'}):
            _, cfg = run_bench.parse_options(['--config', str(path)])
            self.assertEqual(cfg['api_key'], 'environment-key')
            self.assertEqual(cfg['concurrency'], 1)
            _, cfg = run_bench.parse_options(['--config', str(path), '--no-stream'])
            self.assertFalse(cfg['stream'])
            self.assertEqual(cfg['concurrency'], 4)
            _, cfg = run_bench.parse_options(['--api-key', 'explicit-key'])
            self.assertEqual(cfg['api_key'], 'explicit-key')
            self.assertFalse(cfg['stream'])

    @unittest.skipUnless(os.name == 'nt', 'Windows batch launcher')
    def test_batch_launcher_preserves_exit_code_from_other_directory(self):
        for args, expected in ((['--list', '--limit', '1'], 0), (['--list', '--limit', '-1'], 2)):
            result = subprocess.run(
                [str(ROOT / 'run_bench.bat'), '--config', str(ROOT / 'config.example.json'), *args], cwd=self.tmp,
                env={**os.environ, 'PYTHON': sys.executable}, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, expected, result.stderr)

    def test_local_lan_and_cloud_request_routing(self):
        # Replace only the external network boundary: do not contact real providers.
        import io
        for url in ('http://localhost:8000/v1', 'http://192.168.1.10:5001/v1',
                    'https://provider.example/api/v1'):
            with self.subTest(url=url):
                _, cfg = run_bench.parse_options(['--base-url', url, '--api-key', 'cloud-key',
                                                  '--model', 'chosen-model'])
                response = io.BytesIO(b'{"choices":[{"message":{"content":"answer"},"finish_reason":"stop"}]}')
                with mock.patch('urllib.request.urlopen', return_value=response) as transport:
                    text, meta = run_bench.chat(cfg, 'system', 'question')
                self.assertEqual(text, 'answer')
                self.assertNotIn('error', meta)
                req = transport.call_args.args[0]
                self.assertEqual(req.full_url, url + '/chat/completions')
                self.assertEqual(req.get_header('Authorization'), 'Bearer cloud-key')
                self.assertEqual(json.loads(req.data)['model'], 'chosen-model')

    def test_flags_and_file_send_equivalent_requests_and_cli_overrides(self):
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path, self.headers['Authorization'], body))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'choices': [{'message': {'content': '3'},
                                                          'finish_reason': 'stop'}]}).encode())

            def log_message(self, *args):
                pass

        with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server, contextlib.ExitStack() as cleanup:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            cleanup.callback(worker.join)
            cleanup.callback(server.shutdown)
            url = f'http://127.0.0.1:{server.server_port}/v1/'
            cfg = dict(base_url=url, api_key='test-secret', model='test-model', temperature=0.2,
                       max_tokens=42, request_timeout=10, exec_timeout=5, concurrency=2,
                       stream=False, extra_body={'seed': 7})
            path = self.tmp / 'config.json'
            path.write_text(json.dumps(cfg))
            flags = ['--base-url', url, '--api-key', 'test-secret', '--model', 'test-model',
                     '--temperature', '0.2', '--max-tokens', '42', '--request-timeout', '10',
                     '--exec-timeout', '5', '--concurrency', '2', '--extra-body', '{"seed":7}']
            for i, args in enumerate((['-config', str(path)], flags,
                                      ['--config', str(path), '--model', 'override', '--no-stream'])):
                out = self.tmp / str(i)
                result = self.invoke(*args, '--only', 'bash', '--limit', '1', '--outdir', str(out))
                self.assertEqual(result.returncode, 0, result.stderr)
                saved = next(out.glob('*/results.json')).read_text()
                self.assertNotIn('test-secret', saved)
            self.assertEqual(requests[0], requests[1])
            self.assertEqual(requests[0][0], '/v1/chat/completions')
            self.assertEqual(requests[0][1], 'Bearer test-secret')
            self.assertEqual(requests[2][2]['model'], 'override')


if __name__ == '__main__':
    unittest.main()

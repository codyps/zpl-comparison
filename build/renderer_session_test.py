"""Process reuse, retirement, and recovery independent of renderer behavior."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from build import renderer_session as sessions


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(sessions.close_all)
        self.root = Path(self.tmp.name)
        script = self.root / 'adapter.py'
        script.write_text('''import json,os,sys,time
if sys.argv[1] != '--session':
    print('one-shot error', file=sys.stderr)
    sys.exit(7)
for line in sys.stdin:
    request=json.loads(line)
    mode=request['args'][0]
    if mode=='timeout': time.sleep(30)
    if mode=='crash': os._exit(9)
    if mode=='corrupt': print('not JSON',flush=True);continue
    print(json.dumps(dict(id=request['id'],exitCode=1 if mode=='error' else 0,diagnostic=str(os.getpid()))),flush=True)
''')
        self.command = [sys.executable, str(script)]
        self.env = {**os.environ, **{k: self.tmp.name for k in sessions.DYNAMIC_ENV}}

    def run_case(self, mode='ok', timeout=5, identity='one'):
        return sessions.run(self.command, [mode], cwd=self.tmp.name, env=self.env,
                            timeout=timeout, identity=identity)

    def test_reuses_then_retires_and_invalidates_identity(self):
        with patch.object(sessions, 'MAX_REQUESTS', 2):
            first = self.run_case().stderr
            self.assertEqual(first, self.run_case().stderr)
            second = self.run_case().stderr
            self.assertNotEqual(first, second)
            self.assertNotEqual(second, self.run_case(identity='changed').stderr)

    def test_timeout_kills_process_and_next_request_starts_fresh(self):
        first = int(self.run_case().stderr)
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_case('timeout', timeout=0.1)
        with self.assertRaises(ProcessLookupError):
            os.kill(first, 0)
        self.assertNotEqual(first, int(self.run_case().stderr))

    def test_pool_eviction_reaps_the_old_adapter(self):
        with patch.object(sessions, 'MAX_SESSIONS', 1):
            first = int(self.run_case().stderr)
            self.run_case(identity='another')
            with self.assertRaises(ProcessLookupError):
                os.kill(first, 0)

    def test_error_crash_and_protocol_failure_use_one_shot_and_recover(self):
        for mode in ['error', 'crash', 'corrupt']:
            with self.subTest(mode=mode):
                first = self.run_case().stderr
                result = self.run_case(mode)
                self.assertEqual(result.returncode, 7)
                self.assertEqual(result.stderr, b'one-shot error\n')
                self.assertNotEqual(first, self.run_case().stderr)


if __name__ == '__main__':
    unittest.main()

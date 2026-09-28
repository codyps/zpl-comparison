import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).with_name('warbler_cache.py')


class CredentialScopeTest(unittest.TestCase):
    def helper(self, uri):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), 'get'],
            input=json.dumps({'uri': uri}), text=True, capture_output=True,
            env={**os.environ, 'WARBLER_CACHE_CREDENTIAL': 'reader:test-secret'},
            check=True,
        )
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)['headers']

    def test_cache_endpoint_gets_credentials(self):
        for suffix in ('', '/cas/1234', '/ac/1234'):
            self.assertIn('Authorization', self.helper('https://10.77.0.1:9443/zpl-comparison' + suffix))

    def test_other_endpoints_do_not_get_credentials(self):
        for uri in ('https://example.org', 'http://10.77.0.1:9443/zpl-comparison',
                    'https://10.77.0.1:9443/zpl', 'https://10.77.0.1:9443/zpl-comparison-evil'):
            self.assertEqual(self.helper(uri), {})


if __name__ == '__main__':
    unittest.main()

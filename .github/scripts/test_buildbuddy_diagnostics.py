"""Exercise metadata pagination and keep the API credential out of results."""

import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("diagnostics", Path(__file__).with_name("buildbuddy_diagnostics.py"))
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


class DiagnosticsTest(unittest.TestCase):
    def test_follows_pages_and_scopes_requests(self):
        pages = [
            io.BytesIO(json.dumps({"results": [{"actionId": "first"}], "nextPageToken": "next"}).encode()),
            io.BytesIO(json.dumps({"results": [{"actionId": "second"}]}).encode()),
        ]
        with patch.object(diagnostics.urllib.request, "urlopen", side_effect=pages) as open_url:
            result = diagnostics.collect("00000000-0000-0000-0000-000000000001", "test-secret")
        self.assertEqual([r["actionId"] for r in result["results"]], ["first", "second"])
        self.assertNotIn("test-secret", json.dumps(result))
        requests = [call.args[0] for call in open_url.call_args_list]
        self.assertEqual(json.loads(requests[1].data)["pageToken"], "next")
        for request in requests:
            self.assertEqual(request.full_url, "https://app.buildbuddy.io/rpc/BuildBuddyService/GetCacheScoreCard")
            self.assertEqual(json.loads(request.data)["filter"]["search"], "ZplArchive")
            self.assertEqual(request.get_header("X-buildbuddy-api-key"), "test-secret")

    def test_rejects_invalid_invocation_before_network_access(self):
        with patch.object(diagnostics.urllib.request, "urlopen") as open_url:
            with self.assertRaises(ValueError):
                diagnostics.collect("not-a-uuid", "test-secret")
            open_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()

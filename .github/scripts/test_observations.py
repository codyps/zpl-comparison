"""Only published observation bundles can become a pinned fork baseline."""

import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


baseline = module("fetch_baseline")
popularity = module("collect_popularity")


class ObservationPublicationTest(unittest.TestCase):
    def test_resolution_pins_a_complete_published_bundle(self):
        release = dict(tag_name="ci-observations-12-1", draft=False, published_at="2026-10-02",
                       assets=[dict(name="observations.tar.gz", id=1), dict(name="observations.tar.gz.json", id=2)])
        draft = dict(release, draft=True, published_at="2026-10-03")
        lock = dict(schema=1, kind="bundle", revision="a" * 40, sha256="b" * 64,
                    strip_prefix="observations", url="https://unrelated.invalid/data")
        with patch.object(baseline.subprocess, "check_output", side_effect=[json.dumps([draft, release]), json.dumps(lock)]):
            result = baseline.resolve("owner/repository")
        self.assertEqual(result["sha256"], "b" * 64)
        self.assertEqual(result["url"], "https://github.com/owner/repository/releases/download/ci-observations-12-1/observations.tar.gz")

    def test_partial_release_falls_back_to_the_immutable_bootstrap(self):
        with patch.object(baseline.subprocess, "check_output", return_value=json.dumps([
            dict(tag_name="ci-observations-12-1", draft=False, assets=[])
        ])) as request:
            result = baseline.resolve("owner/repository")
        self.assertEqual(result["kind"], "git-archive")
        self.assertEqual(len(result["sha256"]), 64)
        request.assert_called_once()

    def test_popularity_failure_does_not_invent_a_count(self):
        pins = dict(zpl=dict(url="https://github.com/private/source"), public=dict(url="https://github.com/owner/public"))
        with patch.object(popularity.subprocess, "check_output", side_effect=OSError("offline")) as request:
            result = popularity.collect(pins)
        self.assertEqual(result["repositories"], {})
        self.assertIn("owner/public", result["errors"])
        self.assertTrue(result["observed_utc"])
        request.assert_called_once()


if __name__ == "__main__":
    unittest.main()

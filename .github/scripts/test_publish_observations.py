"""Exercise stale publication and the race with a newer main commit."""

import subprocess
import unittest
from unittest.mock import patch

from publish_observations import publish


class ObservationReleaseTests(unittest.TestCase):
    def publish(self):
        return publish("owner/repo", "source-sha", "123", "2", "https://github.com")

    @patch("publish_observations.subprocess.run")
    @patch("publish_observations.main_head", return_value="new-main")
    def test_stale_build_does_not_download_or_publish(self, head, run):
        self.assertFalse(self.publish())
        run.assert_not_called()

    @patch("publish_observations.subprocess.run")
    @patch("publish_observations.main_head", side_effect=["source-sha", "new-main"])
    def test_main_advances_during_download(self, head, run):
        self.assertFalse(self.publish())
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][:3], ["gh", "run", "download"])

    @patch("publish_observations.subprocess.run")
    @patch("publish_observations.main_head", return_value="source-sha")
    def test_current_build_publishes_exact_source_and_assets(self, head, run):
        run.return_value = subprocess.CompletedProcess([], 0, "release-url\n", "")
        self.assertTrue(self.publish())
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["gh", "release", "create", "ci-observations-123-2"])
        self.assertEqual(command[4:6], ["bundle/observations.tar.gz", "bundle/observations.tar.gz.json"])
        self.assertEqual(command[command.index("--target") + 1], "source-sha")

    def test_release_failure_is_skipped_only_for_superseded_permission_race(self):
        for message, latest, skipped in [
            ("HTTP 403: Resource not accessible by integration", "new-main", True),
            ("HTTP 403: Resource not accessible by integration", "source-sha", False),
            ("HTTP 500: Internal Server Error", "new-main", False),
        ]:
            with self.subTest(message=message, latest=latest), \
                    patch("publish_observations.main_head", side_effect=["source-sha", "source-sha", latest]), \
                    patch("publish_observations.subprocess.run", side_effect=[
                        subprocess.CompletedProcess([], 0),
                        subprocess.CompletedProcess(["gh", "release"], 1, "", message),
                    ]):
                if skipped:
                    self.assertFalse(self.publish())
                else:
                    with self.assertRaises(subprocess.CalledProcessError):
                        self.publish()

    @patch("publish_observations.subprocess.run")
    @patch("publish_observations.main_head", side_effect=subprocess.CalledProcessError(1, ["gh", "api"]))
    def test_head_lookup_failure_is_not_treated_as_superseded(self, head, run):
        with self.assertRaises(subprocess.CalledProcessError):
            self.publish()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()

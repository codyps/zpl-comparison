"""Exercise publication against a local bare remote, including branch history."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from publish_reports import BRANCH, git, publish, remote_head


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo, self.remote, self.output = (
            root / "source",
            root / "remote",
            root / "output",
        )
        for path in (self.repo, self.remote, self.output):
            path.mkdir()
        git(self.remote, "init", "--bare")
        git(self.repo, "init", "--initial-branch=main")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "user.email", "test@example.invalid")
        git(self.repo, "config", "commit.gpgsign", "false")
        git(self.repo, "remote", "add", "origin", str(self.remote))
        (self.repo / "source.txt").write_text("source\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "Source root")
        self.source = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        git(self.repo, "push", "origin", "main")
        for name in (
            "README.md",
            "docs/benchmarks/README.md",
            "docs/benchmarks/accuracy/accuracy.svg",
        ):
            path = self.output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("report\n")

    def test_orphan_then_fast_forward_then_unchanged(self):
        (self.repo / "source.txt").write_text("staged change\n")
        git(self.repo, "add", "source.txt")
        before = git(self.repo, "diff", "--cached").stdout
        (self.output / "obsolete.txt").write_text("old\n")
        first = publish(self.repo, self.output, self.source)
        self.assertEqual(
            git(self.repo, "rev-list", "--parents", "-n", "1", first).stdout.strip(),
            first,
        )
        self.assertEqual(
            git(self.repo, "merge-base", self.source, first, check=False).returncode, 1
        )
        self.assertEqual(git(self.repo, "diff", "--cached").stdout, before)
        self.assertEqual(
            git(self.repo, "rev-parse", "HEAD").stdout.strip(), self.source
        )
        (self.output / "obsolete.txt").unlink()
        (self.output / "README.md").write_text("updated\n")
        second = publish(self.repo, self.output, self.source)
        self.assertEqual(
            git(self.repo, "rev-parse", f"{second}^").stdout.strip(), first
        )
        self.assertNotIn(
            "obsolete.txt", git(self.repo, "ls-tree", "--name-only", second).stdout
        )
        self.assertEqual(publish(self.repo, self.output, self.source), second)
        self.assertEqual(remote_head(self.repo, BRANCH), second)
        self.assertEqual(remote_head(self.repo, "refs/heads/main"), self.source)

    def test_stale_build_does_not_publish(self):
        with patch("publish_reports.remote_head", return_value="new-main"):
            self.assertIsNone(publish(self.repo, self.output, self.source))
        self.assertIsNone(remote_head(self.repo, BRANCH))

    def test_main_advancing_during_preparation_does_not_publish(self):
        with patch(
            "publish_reports.remote_head", side_effect=[self.source, None, "new-main"]
        ):
            self.assertIsNone(publish(self.repo, self.output, self.source))
        self.assertIsNone(remote_head(self.repo, BRANCH))

    def test_existing_source_history_is_not_replaced(self):
        git(self.repo, "push", "origin", "main:generated")
        with self.assertRaisesRegex(ValueError, "shares source history"):
            publish(self.repo, self.output, self.source)
        self.assertEqual(remote_head(self.repo, BRANCH), self.source)

    def test_incomplete_output_is_not_published(self):
        (self.output / "README.md").unlink()
        with self.assertRaisesRegex(ValueError, "Incomplete report tree"):
            publish(self.repo, self.output, self.source)
        self.assertIsNone(remote_head(self.repo, BRANCH))


if __name__ == "__main__":
    unittest.main()

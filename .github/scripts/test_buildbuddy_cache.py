"""Check credential isolation and cache-only fallback without a live account."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("buildbuddy", Path(__file__).with_name("buildbuddy_cache.py"))
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


class BuildBuddyCacheTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.rc = self.home / ".bazelrc"
        self.rc.write_text("startup --output_base=/existing/bazel\n")

    def configure(self, key):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            disk = cache.configure(self.home, self.root / "runner", key)
        if key:
            self.assertNotIn(key, output.getvalue())
            self.assertNotIn(key, self.rc.read_text())
        return disk

    def test_missing_key_retains_disk_caching_without_remote_uploads(self):
        disk = self.configure("")
        self.assertTrue(disk.is_dir())
        self.assertIn(f"--disk_cache={disk}", self.rc.read_text())
        self.assertNotIn("--remote_cache", self.rc.read_text())
        self.assertNotIn("--bes_backend", self.rc.read_text())
        self.assertFalse((self.root / "runner/buildbuddy-credentials").exists())

    def test_key_stays_outside_cached_files_and_only_reaches_buildbuddy(self):
        disk = self.configure("test-secret")
        directory = self.root / "runner/buildbuddy-credentials"
        self.assertFalse(directory.is_relative_to(disk))
        self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((directory / "api-key").stat().st_mode), 0o600)
        self.assertIn("--remote_download_outputs=toplevel", self.rc.read_text())
        for uri, allowed in [
            ("grpcs://remote.buildbuddy.io", True),
            ("https://remote.buildbuddy.io:443/path", True),
            ("https://remote.buildbuddy.io.evil.example", False),
            ("https://example.org/remote.buildbuddy.io", False),
            ("http://remote.buildbuddy.io", False),
            ("grpc://remote.buildbuddy.io", False),
            ("https://remote.buildbuddy.io:444", False),
            ("https://user@remote.buildbuddy.io", False),
        ]:
            with self.subTest(uri=uri):
                result = subprocess.run(
                    [str(directory / "helper.py"), "get"],
                    input=json.dumps({"uri": uri}), capture_output=True,
                    text=True, check=True, env={"PATH": os.environ["PATH"]},
                )
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout), {"headers":
                    {"x-buildbuddy-api-key": ["test-secret"]} if allowed else {}})

    def test_reconfiguration_preserves_existing_options_and_can_disable_remote(self):
        self.configure("first")
        self.configure("replacement")
        self.assertEqual(self.rc.read_text().count("--remote_cache="), 1)
        self.configure("")
        self.assertIn("startup --output_base=/existing/bazel", self.rc.read_text())
        self.assertEqual(self.rc.read_text().count("--disk_cache="), 1)
        self.assertNotIn("--credential_helper", self.rc.read_text())
        self.assertNotIn("--remote_cache", self.rc.read_text())


if __name__ == "__main__":
    unittest.main()

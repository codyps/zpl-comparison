import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("refresh", Path(__file__).with_name("refresh_zpl_source.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RefreshTests(unittest.TestCase):
    def test_resolved_checkout_is_recorded_without_changing_other_pins(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "benchmarks/_work/zpl/zpl/Cargo.toml"
            package.parent.mkdir(parents=True)
            package.write_text('[package]\nversion = "0.2.0"\n')
            lock = root / "benchmarks/sources.lock.json"
            original = {"zpl": {"rev": "old", "version": "0.1.0"}, "other": {"rev": "unchanged"}}
            lock.write_text(json.dumps(original))
            with patch.object(module.subprocess, "check_output", side_effect=["a" * 40, ""]), patch.object(module.subprocess, "run") as run:
                module.refresh(root, "/tmp/pinned/bin/cargo")
            actual = json.loads(lock.read_text())
            self.assertEqual(actual["zpl"], {"rev": "a" * 40, "version": "0.2.0"})
            self.assertEqual(actual["other"], original["other"])
            self.assertEqual(run.call_args.args[0][0], "/tmp/pinned/bin/cargo")
            lock.write_text(json.dumps(original))
            with patch.object(module.subprocess, "check_output", side_effect=["b" * 40, ""]), patch.object(module.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "cargo")):
                with self.assertRaises(subprocess.CalledProcessError):
                    module.refresh(root, "/tmp/pinned/bin/cargo")
            self.assertEqual(json.loads(lock.read_text()), original)

    def test_dirty_checkout_is_rejected(self):
        with patch.object(module.subprocess, "check_output", side_effect=["a" * 40, " M zpl/src/lib.rs"]):
            with self.assertRaisesRegex(ValueError, "clean"):
                module.refresh("/tmp", "/tmp/cargo")

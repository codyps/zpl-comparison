"""Verify report transport preserves files and has reproducible archive bytes."""

import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

from build.report_archive import pack, unpack
from build.stage import stage


class ReportArchiveTest(unittest.TestCase):
    def test_round_trip_matches_assembly_and_ignores_source_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / ("long-" * 24 + "é.txt")).write_text("Unicode report content")
            (source / "page.md").write_text("original")
            replacement = root / "replacement"
            replacement.write_text("replacement")
            raster = root / "raster"
            raster.mkdir()
            (raster / "image.png").write_bytes(b"image bytes")
            missing = root / "missing"
            missing.mkdir()
            spec = {"assemble": True, "inputs": [
                [str(source), "docs"], [str(replacement), "docs/page.md"],
                [str(raster), "docs/image.png"], [str(missing), "docs/missing.png"],
            ]}
            stage(spec, root / "expected")
            pack(spec, root / "first.tar")
            for path in [*source.iterdir(), replacement, raster / "image.png"]:
                os.utime(path, (100, 200))
                path.chmod(0o444)
            pack(spec, root / "second.tar")
            self.assertEqual((root / "first.tar").read_bytes(), (root / "second.tar").read_bytes())
            unpack(root / "first.tar", root / "actual")
            def contents(directory):
                return {p.relative_to(directory).as_posix(): p.read_bytes()
                        for p in directory.rglob("*") if p.is_file()}
            self.assertEqual(contents(root / "expected"), contents(root / "actual"))
            self.assertFalse((root / "actual/docs/missing.png").exists())
            self.assertEqual((root / "actual/docs/page.md").read_text(), "replacement")

    def test_failed_validation_does_not_publish_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.tar"
            with self.assertRaises(subprocess.CalledProcessError):
                pack({"assemble": True, "inputs": [], "commands": [["-c", "raise SystemExit(2)"]]}, output)
            self.assertFalse(output.exists())

    def test_unpack_rejects_paths_outside_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with tarfile.open(root / "invalid.tar", "w") as archive:
                archive.addfile(tarfile.TarInfo("../outside"))
            with self.assertRaises(tarfile.FilterError):
                unpack(root / "invalid.tar", root / "report")
            self.assertFalse((root / "outside").exists())


if __name__ == "__main__":
    unittest.main()

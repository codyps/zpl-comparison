"""Offline service replay must preserve the input and output evidence boundary."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import labelary


class LabelaryTests(unittest.TestCase):
    def test_inch_conversion_does_not_truncate_a_dot(self):
        from decimal import Decimal

        for dots in [300, 812, 832, 1218, 1524]:
            self.assertEqual(int(Decimal(labelary.inches(dots)) * 203), dots)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "case.zpl"
        self.source.write_bytes(b"^XA^XZ")
        self.image = self.root / "case.png"
        self.image.write_bytes(b"original service bytes")
        self.row = dict(
            source="case.zpl",
            sha256=labelary.sha(self.source),
            width=10,
            height=20,
            status="rendered",
            image="case.png",
            png_sha256=labelary.sha(self.image),
        )
        self.write()
        self.patch = patch.object(labelary, "REPO", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def write(self, status="complete"):
        (self.root / "captures.json").write_text(
            json.dumps(dict(status=status, cases=[self.row]))
        )

    def replay(self, width=10):
        return labelary.saved_response(self.source, width, 20, self.root)

    def test_replay_matches_source_and_dimensions(self):
        self.assertEqual(self.replay(), self.image)
        with self.assertRaisesRegex(ValueError, "No unique"):
            self.replay(width=11)
        self.source.write_bytes(b"changed input")
        with self.assertRaisesRegex(ValueError, "No unique"):
            self.replay()

    def test_changed_image_and_incomplete_capture_fail(self):
        self.image.write_bytes(b"changed image")
        with self.assertRaisesRegex(ValueError, "Changed Labelary image"):
            self.replay()
        self.write(status="incomplete")
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.replay()

    def test_http_failure_is_not_a_successful_fallback(self):
        self.row.update(status="error", http_status=400, diagnostic="Unsupported input")
        self.write()
        with self.assertRaisesRegex(ValueError, "Labelary HTTP 400"):
            self.replay()

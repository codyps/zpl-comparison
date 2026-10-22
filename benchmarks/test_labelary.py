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

        for dpi in [203, 304]:
            for dots in [300, 812, 832, 1218, 1524, 2558]:
                self.assertEqual(int(Decimal(labelary.inches(dots, dpi)) * dpi), dots)
        self.assertEqual(labelary.request_url(dict(width=832, height=2558), 12),
                         'https://api.labelary.com/v1/printers/12dpmm/labels/2.736843x8.414474/0/')

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

    def test_extension_preserves_existing_response_without_network(self):
        self.row.update(suite="test", name="case")
        self.write()
        case = {
            k: self.row[k]
            for k in ["suite", "name", "source", "sha256", "width", "height"]
        }
        original = self.image.read_bytes()
        with (
            patch.object(labelary, "inputs", return_value=[case]),
            patch.object(labelary.subprocess, "run") as request,
        ):
            labelary.capture(self.root, extend=True)
        request.assert_not_called()
        saved = json.loads((self.root / "captures.json").read_text())
        self.assertEqual(saved["cases"], [self.row])
        self.assertEqual(self.image.read_bytes(), original)
        self.source.write_bytes(b"changed")
        with (
            patch.object(labelary, "inputs", return_value=[case]),
            self.assertRaisesRegex(ValueError, "source/metadata changed"),
        ):
            labelary.capture(self.root, extend=True)

    def test_extension_rejects_a_different_density_before_network(self):
        with (patch.object(labelary, "inputs", return_value=[]),
              patch.object(labelary.subprocess, "run") as request,
              self.assertRaisesRegex(ValueError, "density changed")):
            labelary.capture(self.root, extend=True, dpmm=12)
        request.assert_not_called()

    def test_300dpi_validation_rejects_203dpi_response_metadata(self):
        from PIL import Image
        Image.new('L', (10, 20), 255).save(self.image)
        self.row.update(suite='test', name='case', dpmm=12, dpi=300,
                        dimensions=[10, 20], png_sha256=labelary.sha(self.image))
        self.row['url'] = labelary.request_url(self.row, 12)
        case = {k: self.row[k] for k in ['suite', 'name', 'source', 'sha256', 'width', 'height']}
        manifest = dict(status='complete', dpmm=12, dpi=300, canvas_dpi=304, cases=[self.row])
        path = self.root / 'captures.json'
        with patch.object(labelary, 'inputs', return_value=[case]):
            path.write_text(json.dumps(manifest))
            labelary.validate(self.root, dpmm=12)
            self.row['url'] = labelary.request_url(self.row, 8)
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'request density or canvas mismatch'):
                labelary.validate(self.root, dpmm=12)
            manifest['dpmm'] = 8
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'density mismatch'):
                labelary.validate(self.root, dpmm=12)

    def test_http_failure_is_not_a_successful_fallback(self):
        self.row.update(status="error", http_status=400, diagnostic="Unsupported input")
        self.write()
        with self.assertRaisesRegex(ValueError, "Labelary HTTP 400"):
            self.replay()

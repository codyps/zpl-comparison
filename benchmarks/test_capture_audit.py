"""Integrity and pixel comparisons for independently recaptured references."""

import json
import tempfile
import unittest
from pathlib import Path

from accuracy import audit_captures as audit
from PIL import Image


class CaptureAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.saved = Path(self.tmp.name) / "saved"
        self.fresh = Path(self.tmp.name) / "fresh"
        for directory in (self.saved, self.fresh):
            directory.mkdir()
            cases = []
            for name in ("first", "other", "repeat-end"):
                source = b"^XA^FO1,1^GB1,1,1^FS^XZ"
                (directory / (name + ".zpl")).write_bytes(source)
                Image.new("RGBA", (3, 3), "white").save(directory / (name + ".png"))
                cases.append(
                    {
                        "name": name,
                        "zpl_sha256": audit.sha(source),
                        "png_sha256": audit.sha(
                            (directory / (name + ".png")).read_bytes()
                        ),
                        "captured_utc": "2026-09-21T00:00:00Z",
                        "submitted_sha256": "example",
                    }
                )
            self.write(
                directory,
                {
                    "status": "complete",
                    "repeat_pixels_equal": True,
                    "device": "ZTC ZD621-203dpi ZPL",
                    "firmware": "V93.21.33Z",
                    "dpi": 203,
                    "host": "http://printer/",
                    "method": "HTTP Preview Label",
                    "cases": cases,
                    "captured_utc": "2026-09-21T00:00:00Z",
                    "preview_reset_zpl": "^XA^XZ",
                },
            )

    def write(self, directory, manifest):
        (directory / "manifest.json").write_text(json.dumps(manifest))

    def read(self, directory):
        return json.loads((directory / "manifest.json").read_text())

    def replace_image(self, name, image):
        path = self.fresh / (name + ".png")
        image.save(path)
        manifest = self.read(self.fresh)
        next(r for r in manifest["cases"] if r["name"] == name)["png_sha256"] = (
            audit.sha(path.read_bytes())
        )
        self.write(self.fresh, manifest)

    def test_equal_and_rgb_difference_with_unchanged_alpha(self):
        self.assertEqual(audit.compare(self.saved, self.fresh)["equal"], 3)
        image = Image.new("RGBA", (3, 3), "white")
        image.putpixel((1, 1), (0, 0, 0, 255))
        self.replace_image("other", image)
        result = audit.compare(self.saved, self.fresh)
        self.assertEqual(result["changed"], 1)
        self.assertEqual(result["cases"][1]["changed_pixels"], 1)

    def test_dimension_change_is_not_aligned_away(self):
        self.replace_image("other", Image.new("RGBA", (4, 3), "white"))
        self.assertEqual(audit.compare(self.saved, self.fresh)["changed"], 1)

    def test_tampered_capture_is_rejected(self):
        (self.saved / "other.zpl").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            audit.compare(self.saved, self.fresh)

    def test_repeat_flag_does_not_override_actual_pixels(self):
        self.replace_image("repeat-end", Image.new("RGBA", (3, 3), "black"))
        with self.assertRaisesRegex(ValueError, "repeated control"):
            audit.compare(self.saved, self.fresh)

    def test_missing_captures_are_reported(self):
        manifest = self.read(self.fresh)
        manifest["cases"] = [r for r in manifest["cases"] if r["name"] != "other"]
        self.write(self.fresh, manifest)
        self.assertEqual(
            audit.compare(self.saved, self.fresh)["not_recaptured"], ["other"]
        )


if __name__ == "__main__":
    unittest.main()

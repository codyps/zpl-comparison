"""Comparison publication must reject incomplete or stale render evidence."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from accuracy import gallery


class GalleryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dest = self.root / "output"
        (self.dest / "images").mkdir(parents=True)
        self.patch = patch.object(gallery, "REPO", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        (self.root / "case.zpl").write_text("^XA^FO0,0^GB1,1,1^FS^XZ")
        reference = np.array([[0, 255]], dtype=np.uint8)
        Image.fromarray(reference).save(self.root / "reference.png")
        case = dict(
            id="case",
            name="case",
            group="shapes",
            command="^GB",
            arguments="1,1,1",
            zpl="case.zpl",
            reference="reference.png",
            zpl_sha256=gallery.sha(self.root / "case.zpl"),
            png_sha256=gallery.sha(self.root / "reference.png"),
            printer_dimensions=[2, 1],
        )
        rows = []
        for lib in gallery.LIBRARIES:
            # Include both a valid render and valid blank output.
            raster = reference if lib != "forge" else np.full_like(reference, 255)
            metrics, diff = gallery.compare(reference, raster)
            Image.fromarray(raster).save(self.dest / "images" / f"case-{lib}.png")
            Image.fromarray(diff).save(self.dest / "images" / f"case-{lib}-diff.png")
            rows.append(
                dict(
                    case="case",
                    library=lib,
                    status="rendered" if metrics["output_ink"] else "blank",
                    score=metrics["iou"],
                    **metrics,
                )
            )
        rows[0] = dict(
            case="case",
            library="codyps-zpl",
            status="error",
            score=0,
            reference_ink=1,
            error="Unsupported command",
        )
        self.data = dict(
            cases=[case], results=rows, measured_utc="2026-09-18T00:00:00Z"
        )

    def test_error_and_blank_are_visible(self):
        pages = gallery.pages(self.data, self.dest)
        page = pages[Path("comparisons/cases/case.md")]
        self.assertIn("Unsupported command", page)
        self.assertIn("blank output", page)
        self.assertIn("![forge render](../../previews/case-forge.png)", page)
        self.assertIn("](../../images/case-forge.png)", page)
        self.assertNotIn("![codyps-zpl render]", page)
        library = pages[Path("comparisons/libraries/forge.md")]
        self.assertIn(
            "![forge difference](../../previews/case-forge-diff.png)", library
        )
        self.assertIn("](../../images/case-forge-diff.png)", library)
        self.assertNotIn(
            "![codyps-zpl difference]",
            pages[Path("comparisons/libraries/codyps-zpl.md")],
        )
        self.assertEqual(len(pages), len(gallery.LIBRARIES) + 1)

    def test_changed_labelary_snapshot_requires_new_measurement(self):
        snapshot = self.root / "docs/benchmarks/labelary/captures.json"
        snapshot.parent.mkdir(parents=True)
        snapshot.write_text("new service snapshot")
        data = {
            **self.data,
            "adapters": {"labelary": [{"name": "captures.json", "sha256": "old"}]},
        }
        with self.assertRaisesRegex(ValueError, "Labelary snapshot changed"):
            gallery.validate(data, self.dest)

    def test_missing_and_duplicate_attempts_are_rejected(self):
        for rows in [
            self.data["results"][:-1],
            self.data["results"] + [self.data["results"][0]],
        ]:
            data = {**self.data, "results": rows}
            with self.assertRaisesRegex(ValueError, "exactly one"):
                gallery.validate(data, self.dest)

    def test_missing_image_is_rejected(self):
        (self.dest / "images/case-forge.png").unlink()
        with self.assertRaises(FileNotFoundError):
            gallery.validate(self.data, self.dest)

    def test_regeneration_rebuilds_deleted_derived_diff_and_keeps_evidence(self):
        snapshot = self.dest / "results.json"
        snapshot.write_text(json.dumps(self.data))
        original = snapshot.read_bytes()
        target = self.dest / "images/case-forge-diff.png"
        expected = target.read_bytes()
        target.unlink()
        gallery.generate(self.dest)
        self.assertTrue(target.exists())
        gallery.generate(self.dest, check=True)
        self.assertEqual(snapshot.read_bytes(), original)
        with Image.open(target) as actual:
            import io

            with Image.open(io.BytesIO(expected)) as prior:
                self.assertEqual(actual.tobytes(), prior.tobytes())

    def test_wrong_diff_is_rejected(self):
        Image.new("RGB", (2, 1), "white").save(self.dest / "images/case-forge-diff.png")
        with self.assertRaisesRegex(ValueError, "Stale difference"):
            gallery.validate(self.data, self.dest)

    def test_stale_metric_and_reference_are_rejected(self):
        data = copy.deepcopy(self.data)
        data["results"][1]["iou"] = 0.5
        with self.assertRaisesRegex(ValueError, "Stale iou"):
            gallery.validate(data, self.dest)
        (self.root / "case.zpl").write_text("^XA^XZ")
        with self.assertRaisesRegex(ValueError, "Changed zpl"):
            gallery.validate(self.data, self.dest)


if __name__ == "__main__":
    unittest.main()

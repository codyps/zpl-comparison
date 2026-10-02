"""Accuracy metric and capture-integrity regression tests; never contact a printer."""

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "accuracy_runner", ROOT / "accuracy/run.py"
)
accuracy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accuracy)


class AccuracyTests(unittest.TestCase):
    def test_missing_extra_and_origin_are_not_aligned_away(self):
        ref = np.array([[0, 0, 255], [255, 255, 255]], dtype=np.uint8)
        out = np.array([[255, 0, 0], [255, 255, 255]], dtype=np.uint8)
        metrics, diff = accuracy.compare(ref, out)
        self.assertAlmostEqual(metrics["iou"], 1 / 3)
        self.assertEqual((metrics["missing"], metrics["extra"]), (1, 1))
        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertEqual(diff[0, 0].tolist(), [220, 0, 150])
        self.assertEqual(diff[0, 2].tolist(), [0, 160, 220])

    def test_canvas_size_is_separate_from_ink_match(self):
        metrics, _ = accuracy.compare(np.array([[0, 255]]), np.array([[0]]))
        self.assertTrue(metrics["ink_exact"])
        self.assertFalse(metrics["exact"])
        self.assertFalse(metrics["dimensions_match"])
        self.assertEqual(metrics["iou"], 1)

    def test_empty_output_does_not_score_for_white_background(self):
        metrics, _ = accuracy.compare(np.array([[0, 255, 255]]), np.full((1, 3), 255))
        self.assertEqual(metrics["iou"], 0)
        self.assertEqual(metrics["output_ink"], 0)

    def test_transparency_and_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transparent.png"
            image = Image.new("RGBA", (3, 1))
            image.putdata([(0, 0, 0, 0), (127, 127, 127, 255), (128, 128, 128, 255)])
            image.save(path)
            self.assertEqual(accuracy.gray(path).tolist(), [[255, 127, 128]])

    def test_checked_in_corpus_integrity(self):
        cases, _, _ = accuracy.corpus()
        self.assertEqual(len(cases), 133)
        self.assertEqual(len({c["id"] for c in cases}), 133)

    def test_corruption_and_unstable_capture_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "reference"
            shutil.copytree(ROOT / "accuracy/reference", dest)
            manifest_path = dest / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["status"] = "unstable"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Unstable"):
                accuracy.corpus(dest)
            manifest["status"] = "complete"
            manifest_path.write_text(json.dumps(manifest))
            (dest / "repeat-end.png").write_bytes(b"corrupted")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                accuracy.corpus(dest)

    def test_capture_sources_match_deterministic_probes(self):
        probe_spec = importlib.util.spec_from_file_location(
            "accuracy_cases", ROOT / "accuracy/cases.py"
        )
        probes = importlib.util.module_from_spec(probe_spec)
        probe_spec.loader.exec_module(probes)
        for case in probes.probes():
            self.assertEqual(
                (ROOT / "accuracy/reference" / (case["name"] + ".zpl")).read_bytes(),
                case["zpl"],
            )

    def test_repeat_pixels_checked_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "reference"
            shutil.copytree(ROOT / "accuracy/reference", dest)
            image_path = dest / "repeat-end.png"
            with Image.open(image_path) as original:
                image = original.convert("RGB")
            image.putpixel((0, 0), (0, 0, 0))
            image.save(image_path)
            manifest_path = dest / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["cases"][-1]["png_sha256"] = accuracy.sha(image_path)
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Repeated control"):
                accuracy.corpus(dest)



if __name__ == "__main__":
    unittest.main()

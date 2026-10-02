"""The public campaign must retain native canvases and real service failures."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

import public_examples as public


class PublicComparisonTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.output = self.root / "report"
        (self.output / "images").mkdir(parents=True)
        (self.root / "manifest.json").write_text("{}")
        for obj, field in [(public, "ROOT"), (public, "CORPUS"),
                           (public, "REFERENCE"), (public.labelary, "DEFAULT")]:
            stack.enter_context(patch.object(obj, field, self.root))
        self.case = dict(name="sample")
        self.reference = np.array([[0, 255], [255, 255]], dtype=np.uint8)
        self.row = dict(suite="public-zpl", name="sample", sha256="source-hash",
                        status="rendered", requested_utc="start", received_utc="end",
                        url="recorded-url", http_status=200, renderer_version=None,
                        image="response.png")
        self.captures = dict(service="recorded-service", identity="UTC timestamps",
                             cases=[self.row])
        stack.enter_context(patch.object(public.labelary, "validate", return_value=self.captures))

    def render(self, pixels):
        path = self.root / self.row["image"]
        Image.fromarray(np.array(pixels, dtype=np.uint8)).save(path)
        self.row["png_sha256"] = public.sha(path)

    def compare(self, check=False):
        return public.service_comparisons(self.output, [self.case],
                                          {"sample": self.reference}, check=check)

    def test_native_counts_and_modified_difference_detection(self):
        self.render([[255, 0], [255, 255]])
        saved = self.compare()
        row = saved["results"][0]
        self.assertEqual(row["comparison"]["iou"], 0)
        self.assertEqual(row["comparison"]["missing"], 1)
        self.assertEqual(row["comparison"]["extra"], 1)
        self.assertEqual(self.compare(check=True), saved)
        Image.new("RGB", (2, 2), "white").save(self.output / row["diff"])
        with self.assertRaisesRegex(ValueError, "Changed Labelary difference"):
            self.compare(check=True)

    def test_unequal_canvas_is_unscored_even_when_ink_matches(self):
        self.render([[0, 255, 255], [255, 255, 255]])
        row = self.compare()["results"][0]
        self.assertEqual(row["comparison_status"], "canvas_mismatch")
        self.assertEqual(row["output_dimensions"], [3, 2])
        self.assertNotIn("comparison", row)
        self.assertNotIn("diff", row)

    def test_real_error_and_missing_capture_are_not_fabricated(self):
        self.row.update(status="error", http_status=400, diagnostic="Unsupported input")
        row = self.compare()["results"][0]
        self.assertEqual(row["diagnostic"], "Unsupported input")
        self.assertNotIn("image", row)
        self.assertNotIn("comparison", row)
        self.captures["cases"] = []
        with self.assertRaisesRegex(ValueError, "Incomplete public Labelary"):
            self.compare()


if __name__ == "__main__":
    unittest.main()

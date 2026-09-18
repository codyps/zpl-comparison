"""Regression tests for measurement boundaries and rejection of bad outputs."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image, ImageDraw
from run import check_output, measure, node_files


class HarnessTests(unittest.TestCase):
    def test_child_rss_and_json_are_per_process(self):
        script = "import json; data=bytearray(32*1024*1024); print(json.dumps(dict(ns=123, iterations=1, checksum=len(data))))"
        result = measure([sys.executable, "-c", script], os.environ.copy())
        self.assertEqual(result["iterations"], 1)
        self.assertEqual(result["checksum"], 32 * 1024 * 1024)
        self.assertGreater(result["peak_rss_bytes"], 32 * 1024 * 1024)

    def test_timeout_and_nonzero_exit_fail(self):
        with self.assertRaisesRegex(RuntimeError, "Timed out"):
            measure(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                os.environ.copy(),
                timeout=0.1,
            )
        with self.assertRaisesRegex(RuntimeError, "Exit 7"):
            measure([sys.executable, "-c", "raise SystemExit(7)"], os.environ.copy())

    def test_png_oracle_and_invalid_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "image.png"
            image = Image.new("RGB", (400, 300), "white")
            image.save(path)
            with self.assertRaisesRegex(RuntimeError, "Blank"):
                check_output(path, "png", "boxes")
            draw = ImageDraw.Draw(image)
            draw.rectangle((20, 20, 119, 79), outline="black", width=4)
            draw.rectangle((180, 100, 259, 179), fill="black")
            image.save(path)
            result = check_output(path, "png", "boxes")
            self.assertEqual(result["box_pixel_mismatches"], 0)
            self.assertEqual(result["black_pixels"], 7616)
            Image.new("RGB", (1, 1), "black").save(path)
            with self.assertRaisesRegex(RuntimeError, "Unexpected image"):
                check_output(path, "png", "boxes")

    def test_generator_cannot_skip_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "label.zpl"
            path.write_text("^XA^FDItem 00^FS^XZ")
            self.assertEqual(check_output(path, "generate", "fields-1")["fields"], 1)
            with self.assertRaisesRegex(RuntimeError, "Wrong field count"):
                check_output(path, "generate", "fields-48")

    def test_node_closure_isolated(self):
        if not (Path(__file__).parent / "adapters/node/node_modules/jszpl").exists():
            self.skipTest("Node dependencies not installed")
        self.assertTrue(any("skia-canvas" in str(p) for p in node_files("zplr")))
        self.assertFalse(any("skia-canvas" in str(p) for p in node_files("jszpl")))


if __name__ == "__main__":
    unittest.main()

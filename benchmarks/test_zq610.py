import importlib.util
import json
from pathlib import Path
import unittest
from PIL import Image

spec = importlib.util.spec_from_file_location("zq610", Path(__file__).with_name("zq610.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Zq610Tests(unittest.TestCase):
    def test_every_native_case_has_a_verified_labelary_observation(self):
        root = module.ROOT
        manifest = json.loads((root / "references/zq610-candidates/manifest.json").read_text())
        native = {row["name"]: row for row in manifest["cases"]}
        service = manifest["labelary"]
        self.assertEqual(len(native), 120)
        self.assertEqual(len(service), len(native))
        self.assertEqual({row["name"] for row in service}, set(native))
        for row in service:
            case = native[row["name"]]
            self.assertEqual(row["sha256"], case["sha256"])
            self.assertEqual(row["status"], "rendered")
            image = root / "references/zq610-candidates/labelary" / row["image"]
            self.assertEqual(module.sha(image.read_bytes()), row["png_sha256"])
            self.assertEqual(module.sha((root / case["source"]).read_bytes()), case["sha256"])
            self.assertEqual(module.sha((root / case["reference"]).read_bytes()), case["png_sha256"])

    def test_native_canvas_must_match(self):
        a, b = Image.new("L", (384, 200), 255), Image.new("L", (832, 200), 255)
        self.assertFalse(module.metrics(a, b)["dimensions_equal"])
        self.assertFalse(module.metrics(a, b)["exact"])

    def test_directional_ink_at_original_origin(self):
        a, b = Image.new("L", (10, 10), 255), Image.new("L", (10, 10), 255)
        a.putpixel((1, 1), 0)
        b.putpixel((2, 1), 0)
        result = module.metrics(a, b)
        self.assertEqual(result["underpaint"], 1)
        self.assertEqual(result["overpaint"], 1)
        self.assertEqual(result["foreground_iou"], 0)
        self.assertFalse(result["exact"])

    def test_blank_is_not_positive_accuracy_evidence(self):
        a = Image.new("L", (10, 10), 255)
        result = module.metrics(a, a)
        self.assertIsNone(result["foreground_iou"])
        self.assertFalse(result["nonblank"])

    def test_prepared_barcode_and_replacement_geometry(self):
        root = module.ROOT / "references/zq610-plus-v1"
        manifest = json.loads((root / "manifest.json").read_text())
        module.verify(root, manifest)
        count = 0
        for name, row in manifest["cases"].items():
            if name.startswith("barcode-") or name.endswith("-fit"):
                self.assertTrue(row["fits_narrow_width"], name)
                self.assertLess(row["predicted"]["bbox"][2], 384, name)
                count += 1
        self.assertEqual(count, 67)


if __name__ == "__main__":
    unittest.main()

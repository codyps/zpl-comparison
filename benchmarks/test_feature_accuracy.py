"""Feature gallery integrity and score boundaries on small synthetic rasters."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from accuracy import features


class FeatureAccuracyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for name, value in [
            ("REPO", root),
            ("CORPUS", root / "corpus"),
            ("RENDERS", root / "renders"),
            ("REFERENCES", root / "refs"),
            ("DEST", root / "gallery"),
        ]:
            value.mkdir(exist_ok=True)
            patcher = patch.object(features, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        (features.RENDERS / "images").mkdir()
        (features.CORPUS / "manifest.json").write_text("{}")
        self.cases = []
        self.rows = []
        for name in ["ink", "blank", "invalid", "unavailable"]:
            path = features.CORPUS / (name + ".zpl")
            path.write_text(name)
            case = dict(
                name=name,
                validity="invalid" if name == "invalid" else "valid",
                capture_eligible=name != "invalid",
                sha256=features.sha(path),
                path=path,
                group="test",
                purpose=name,
                oracle="printer",
            )
            self.cases.append(case)
            for lib in features.LIBRARIES:
                raster = np.zeros((2, 2), dtype=np.uint8)
                Image.fromarray(raster).save(
                    features.RENDERS / "images" / f"{name}-{lib}.png"
                )
                self.rows.append(
                    dict(
                        case=name,
                        library=lib,
                        status="rendered",
                        width=2,
                        height=2,
                        ink=4,
                        diagnostic="",
                    )
                )
        self.rows[0].update(status="error", diagnostic="example failure")
        self.data = dict(
            manifest_sha256=features.sha(features.CORPUS / "manifest.json"),
            measured_utc="test",
            cases=[{k: v for k, v in c.items() if k != "path"} for c in self.cases],
            results=self.rows,
        )
        self.save_data()
        reference = dict(
            corpus_sha256=self.data["manifest_sha256"],
            device="test printer",
            firmware="test",
            captured_utc="test",
            failures=[
                dict(
                    name="unavailable",
                    zpl_sha256=self.cases[-1]["sha256"],
                    error="HTTP 404",
                )
            ],
        )
        (features.REFERENCES / "manifest.json").write_text(json.dumps(reference))
        (features.REFERENCES / "unavailable.zpl").write_text("unavailable")
        for name in ["ink", "blank"]:
            Image.new("L", (2, 2), 0 if name == "ink" else 255).save(
                features.REFERENCES / (name + ".png")
            )
        patcher = patch.object(features, "load_cases", return_value=({}, self.cases))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(
            features,
            "reference_images",
            return_value=(
                reference,
                {
                    "ink": np.zeros((2, 2), dtype=np.uint8),
                    "blank": np.full((2, 2), 255, dtype=np.uint8),
                },
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def save_data(self):
        (features.RENDERS / "results.json").write_text(json.dumps(self.data))

    def test_scores_and_visible_failures(self):
        features.generate()
        features.generate(check=True)
        results = json.loads((features.DEST / "results.json").read_text())["results"]
        index = (features.DEST / "README.md").read_text()
        for lib in features.LIBRARIES:
            self.assertIn(f"[{features.NAMES[lib]} IoU](libraries/{lib}.md)", index)
        self.assertIn("| 0.00% · error | 100.00%", index)
        self.assertIn("unscored", index)
        self.assertEqual(results[0]["score"], 0)
        self.assertEqual(results[1]["score"], 1)
        self.assertTrue(all(r["score"] is None for r in results if r["case"] != "ink"))
        page = (features.DEST / "cases/ink.md").read_text()
        library = (features.DEST / "libraries/labelize.md").read_text()
        self.assertIn(
            f"![{features.NAMES['labelize']} difference](../previews/ink-labelize-diff.png)",
            library,
        )
        self.assertIn("](../images/ink-labelize-diff.png)", library)
        self.assertIn("example failure", page)
        self.assertIn("Printer preview", page)
        self.assertIn("-diff.png", page)
        self.assertNotIn("-diff.png", (features.DEST / "cases/invalid.md").read_text())
        self.assertIn("HTTP 404", (features.DEST / "cases/unavailable.md").read_text())

    def test_missing_references_publish_renders_without_scores(self):
        (features.REFERENCES / "manifest.json").unlink()
        features.generate()
        results = json.loads((features.DEST / "results.json").read_text())["results"]
        self.assertTrue(all(r["score"] is None for r in results))
        self.assertIn(
            "Printer references pending", (features.DEST / "README.md").read_text()
        )
        self.assertIn("render]", (features.DEST / "cases/ink.md").read_text())
        self.assertNotIn("-diff.png", (features.DEST / "cases/ink.md").read_text())

    def test_missing_and_duplicate_results_fail(self):
        self.data["results"] = self.rows[:-1]
        with self.assertRaisesRegex(ValueError, "exactly one"):
            features.validate(self.data, self.cases)
        self.data["results"] = self.rows + [self.rows[0]]
        with self.assertRaisesRegex(ValueError, "exactly one"):
            features.validate(self.data, self.cases)

    def test_stale_diff_rejected(self):
        features.generate()
        diff = next((features.DEST / "images").glob("*.png"))
        Image.new("RGB", (2, 2), "red").save(diff)
        with self.assertRaisesRegex(ValueError, "Stale difference"):
            features.generate(check=True)

    def test_stale_raster_rejected(self):
        features.generate()
        Image.new("L", (2, 2), 255).save(
            features.RENDERS / "images" / f"ink-{features.LIBRARIES[1]}.png"
        )
        with self.assertRaisesRegex(ValueError, "Stale render"):
            features.generate(check=True)

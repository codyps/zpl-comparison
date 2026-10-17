"""Cross-host image provenance, suite coverage and comparison policy."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from benchmarks import zplkit


class ZPLKitImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.artifact = self.root / "artifact"
        self.reports = self.root / "reports"
        pin = dict(url="https://github.com/jonathanspiva/zplkit", rev="a" * 40, version="1.1.0")
        zplkit.write(self.root / "benchmarks/sources.lock.json", {"zplkit": pin})
        for relative in zplkit.ADAPTER_FILES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("adapter source")
        self.identity = dict(source=pin, adapter_files={p: zplkit.sha(self.root / p) for p in zplkit.ADAPTER_FILES})
        self.definitions, results = [], []
        for suite in ["accuracy", *zplkit.COMPARISONS, "zq610-candidates", "public", "paired"]:
            reference = "references/" + suite + ".png"
            target = self.reports / reference
            target.parent.mkdir(parents=True, exist_ok=True)
            Image.new("L", (5, 5), 0).save(target)
            case = dict(suite=suite, case="sample", source="sample.zpl", source_sha256="s" * 64,
                        requested_dimensions=[5, 5], reference=reference, reference_sha256=zplkit.sha(target))
            self.definitions.append(case)
            image = "images/" + suite + ".png"
            (self.artifact / image).parent.mkdir(parents=True, exist_ok=True)
            Image.new("L", (5, 5), 0).save(self.artifact / image)
            results.append(dict(case, library="zplkit", status="rendered", image=image,
                                raw_png_sha256=zplkit.sha(self.artifact / image), observed_utc="2026-10-16T00:00:00Z"))
            doc = dict(cases=[dict(name="sample")], libraries=["go"],
                       results=[dict(case="sample", library="go", status="rendered")])
            zplkit.write(self.reports / zplkit.result_path(suite), doc)
            if suite in zplkit.COMPARISONS:
                path = "docs/benchmarks/accuracy/comparisons/" + zplkit.COMPARISONS[suite] + "/results.json"
                zplkit.write(self.reports / path, dict(inputs={}, coverage={}, results=doc["results"]))
        self.data = dict(schema=1, library="zplkit", adapter=self.identity, results=results)
        self.save()

    def save(self):
        zplkit.write(self.artifact / "observations.json", self.data)

    def verify(self):
        return zplkit.verified(self.root, self.artifact, self.definitions)

    def merge(self):
        self.save()
        with patch.object(zplkit, "cases", return_value=self.definitions):
            zplkit.merge(self.root, self.artifact, self.reports)

    def test_imports_all_suites_and_keeps_existing_observations(self):
        self.merge()
        for case in self.definitions:
            doc = zplkit.read(self.reports / zplkit.result_path(case["suite"]))
            self.assertEqual(doc["libraries"], ["go", "zplkit"])
            self.assertEqual(doc["results"][0], dict(case="sample", library="go", status="rendered"))
            if case["suite"] in zplkit.COMPARISONS:
                path = "docs/benchmarks/accuracy/comparisons/" + zplkit.COMPARISONS[case["suite"]] + "/results.json"
                doc = zplkit.read(self.reports / path)
                self.assertEqual(doc["inputs"][zplkit.result_path(case["suite"])], zplkit.sha(self.reports / zplkit.result_path(case["suite"])))
            row = doc["results"][-1]
            self.assertEqual(row["score"], 1.0)
            self.assertEqual(row["adapter"], self.identity)
            self.assertTrue((self.reports / row["image"]).is_file())
            self.assertTrue((self.reports / row["diff"]).is_file())

    def test_native_canvas_mismatch_is_visible_and_unscored(self):
        row = next(r for r in self.data["results"] if r["suite"] == "public")
        Image.new("L", (4, 5), 0).save(self.artifact / row["image"])
        row["raw_png_sha256"] = zplkit.sha(self.artifact / row["image"])
        self.merge()
        row = zplkit.read(self.reports / zplkit.result_path("public"))["results"][-1]
        self.assertEqual(row["comparison_status"], "canvas_mismatch")
        self.assertIsNone(row["score"])
        self.assertNotIn("diff", row)
        self.assertNotIn("comparison", row)

    def test_errors_remain_unscored_in_campaigns_but_zero_in_accuracy(self):
        for row in self.data["results"]:
            row.update(status="error", diagnostic="unsupported input")
            del row["image"]
            del row["raw_png_sha256"]
        self.merge()
        for suite, expected in [("accuracy", 0.0), ("public", None), ("zq610-candidates", None)]:
            row = zplkit.read(self.reports / zplkit.result_path(suite))["results"][-1]
            self.assertEqual(row["score"], expected)
            self.assertNotIn("image", row)

    def test_rejects_missing_and_duplicate_observations(self):
        for replacement in [self.data["results"][:-1], self.data["results"] + [self.data["results"][0]]]:
            with self.subTest(count=len(replacement)):
                zplkit.write(self.artifact / "observations.json", {**self.data, "results": replacement})
                with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
                    self.verify()

    def test_rejects_stale_source_canvas_and_adapter_identity(self):
        for field, value in [("source_sha256", "bad"), ("requested_dimensions", [1, 1])]:
            original = self.data["results"][0][field]
            self.data["results"][0][field] = value
            self.save()
            with self.assertRaisesRegex(ValueError, "Stale ZPLKit fixture"):
                self.verify()
            self.data["results"][0][field] = original
        self.data["adapter"]["source"]["rev"] = "b" * 40
        self.save()
        with self.assertRaisesRegex(ValueError, "source identity"):
            self.verify()

    def test_rejects_modified_image_or_path_escape(self):
        row = self.data["results"][0]
        Image.new("L", (5, 5), 255).save(self.artifact / row["image"])
        with self.assertRaisesRegex(ValueError, "Changed ZPLKit PNG"):
            self.verify()
        row["image"] = "../outside.png"
        self.save()
        with self.assertRaisesRegex(ValueError, "Unsafe observation path"):
            self.verify()

    def test_rejects_destination_coverage_drift(self):
        path = self.reports / zplkit.result_path("accuracy")
        doc = zplkit.read(path)
        doc["cases"].append(dict(name="new-case"))
        zplkit.write(path, doc)
        with self.assertRaisesRegex(ValueError, "Report fixture coverage differs"):
            self.merge()

    def test_rejects_reimport(self):
        self.merge()
        with self.assertRaisesRegex(ValueError, "already imported"):
            self.merge()


if __name__ == "__main__":
    unittest.main()

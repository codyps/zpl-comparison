"""Corpus determinism, rendering-only scope, counted data, and honest oracles."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image
import conformance

ROOT = Path(__file__).resolve().parent
SUITE = ROOT.parent / "test-data/render-conformance"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


generator = module("corpus_generator", SUITE / "generate.py")
sys.path.insert(0, str(ROOT / "accuracy"))
try:
    capture = module("corpus_capture", ROOT / "accuracy/capture.py")
finally:
    sys.path.pop(0)


class ConformanceTests(unittest.TestCase):
    def test_references_require_matching_bytes_and_stable_control(self):
        _, cases = conformance.load_cases(groups=["metamorphic"])
        case = cases[0]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            rows = []
            for name in [case["name"], "repeat-end"]:
                source = directory / (name + ".zpl")
                png = directory / (name + ".png")
                source.write_bytes(case["path"].read_bytes())
                Image.new("L", (2, 2), 0).save(png)
                rows.append(
                    dict(
                        name=name,
                        zpl_sha256=conformance.metrics.sha(source),
                        png_sha256=conformance.metrics.sha(png),
                    )
                )
            manifest = dict(status="complete", repeat_pixels_equal=True, cases=rows)
            path = directory / "manifest.json"
            path.write_text(json.dumps(manifest))
            _, images = conformance.reference_images(directory, cases)
            self.assertEqual(set(images), {case["name"]})
            with self.assertRaisesRegex(ValueError, "different input"):
                conformance.reference_images(directory, [{**case, "sha256": "wrong"}])
            (directory / "repeat-end.zpl").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                conformance.reference_images(directory, cases)

    def test_generated_files_and_inventory_are_current(self):
        generated = generator.artifacts()
        for filename, data in generated.items():
            self.assertEqual((SUITE / filename).read_bytes(), data, filename)
        self.assertEqual(
            {str(p.relative_to(SUITE)) for p in (SUITE / "cases").rglob("*.zpl")},
            {n for n in generated if n.endswith(".zpl")},
        )
        manifest = json.loads(generated["manifest.json"])
        commands = {cmd for c in manifest["cases"] for cmd in c["commands"]}
        self.assertEqual(commands, {"^" + code for code in generator.ALLOWED})
        self.assertTrue(all(c["references"] for c in manifest["cases"]))
        self.assertEqual(
            len({c["name"] for c in manifest["cases"]}), len(manifest["cases"])
        )

    def test_binary_prefixes_are_data_not_commands(self):
        data = b"^XA^FO0,0^GFB,8,8,1,^FS~HS\x00\xff^FS^XZ"
        self.assertEqual(generator.commands(data), ["^FO", "^FS", "^GF", "^XA", "^XZ"])
        with self.assertRaisesRegex(ValueError, "Control command"):
            generator.commands(data + b"~HS")
        for forbidden in [b"^XF", b"^A@", b"^DF", b"^PQ", b"^MD", b"^JUS", b"^RF"]:
            with self.assertRaises(ValueError):
                generator.commands(b"^XA" + forbidden + b"^XZ")

    def test_capture_excludes_invalid_and_appends_control(self):
        _, rows = conformance.load_cases(invalid=True)
        probes = capture.corpus_probes(SUITE)
        invalid = {r["name"] for r in rows if r["validity"] == "invalid"}
        self.assertTrue(invalid)
        self.assertTrue(invalid.isdisjoint({p["name"] for p in probes}))
        self.assertEqual(probes[0]["zpl"], probes[-1]["zpl"])
        self.assertEqual(probes[-1]["name"], "repeat-end")
        torture = capture.corpus_probes(SUITE, ["torture"])
        self.assertEqual(len(torture), 5)
        with self.assertRaisesRegex(ValueError, "No capture-eligible"):
            capture.corpus_probes(SUITE, ["negative"])

    def test_relation_does_not_pass_blank_or_failed_images(self):
        cases = [{"name": n, "relation": {"set": "test"}} for n in ["a", "b"]]
        results = {("local", n): {"status": "blank"} for n in ["a", "b"]}
        self.assertEqual(
            conformance.relations(cases, results, {}, ["local"])[0]["status"],
            "inconclusive",
        )
        for r in results.values():
            r["status"] = "rendered"
        images = {
            ("local", "a"): np.array([[0, 255]]),
            ("local", "b"): np.array([[0, 255]]),
        }
        self.assertEqual(
            conformance.relations(cases, results, images, ["local"])[0]["status"],
            "equal",
        )
        images[("local", "b")] = np.array([[255, 0]])
        self.assertEqual(
            conformance.relations(cases, results, images, ["local"])[0]["status"],
            "different",
        )

    def test_raster_relation_vectors_are_not_vacuous_duplicates(self):
        _, cases = conformance.load_cases(groups=["graphics"])
        members = [
            c for c in cases if c["relation"] and c["relation"]["set"] == "inline-16x8"
        ]
        self.assertEqual(len(members), 4)
        self.assertEqual(len({c["sha256"] for c in members}), 4)
        self.assertTrue(all(c["width"] == 832 and c["height"] == 1218 for c in members))


if __name__ == "__main__":
    unittest.main()

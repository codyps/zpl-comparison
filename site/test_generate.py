"""Publication contracts: scoring, evidence safety and navigable static output."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image

spec = importlib.util.spec_from_file_location(
    "generate", Path(__file__).with_name("generate.py")
)
generate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate)


class PublicationTests(unittest.TestCase):
    def test_unscored_is_not_zero_and_failure_zero_is_preserved(self):
        self.assertEqual(
            generate.summary([{"score": 1}, {"score": 0}, {"score": None}]), (0.5, 2, 3)
        )
        self.assertEqual(generate.summary([{"score": None}]), (None, 0, 1))
        self.assertIn("No observations", generate.heat([], "case.html"))
        self.assertIn("Unscored", generate.heat([{"score": None}], "case.html"))

    def test_missing_and_escaping_evidence_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "input").mkdir()
            s = generate.Site(root / "input", root / "output")
            with self.assertRaisesRegex(ValueError, "Missing evidence"):
                s.asset("missing.png")
            self.assertIsNone(s.asset("missing.png", required=False))
            with self.assertRaisesRegex(ValueError, "escapes"):
                s.asset("../private.png")

    def test_assets_deduplicate_without_publishing_source_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input"
            source.mkdir()
            (source / "first.zpl").write_text("^XA^XZ")
            (source / "second.zpl").write_text("^XA^XZ")
            (source / "README.md").write_text("internal instructions")
            s = generate.Site(source, root / "output")
            self.assertEqual(s.asset("first.zpl"), s.asset("second.zpl"))
            self.assertEqual(len(list(s.output.rglob("*.zpl"))), 1)
            self.assertFalse(list(s.output.rglob("*.md")))

    def test_link_checker_requires_files_and_fragments(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.html").write_text('<a href="case.html#go">Result</a>')
            with self.assertRaisesRegex(ValueError, "Broken local link"):
                generate.validate(root)
            (root / "case.html").write_text("<h1>Case</h1>")
            with self.assertRaisesRegex(ValueError, "Broken fragment"):
                generate.validate(root)
            (root / "case.html").write_text('<h1 id="go">Case</h1>')
            generate.validate(root)

    def test_methodology_is_linked_at_most_once_per_page(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "methodology.html").write_text('<h1 id="scores">Methodology</h1>')
            (root / "categories").mkdir()
            page = root / "categories/layout.html"
            nav = '<a href="../methodology.html">Reading the results</a>'
            page.write_text(nav)
            generate.validate(root)
            for extra in ("../methodology.html#scores", "http://127.0.0.1:8873/methodology.html", "../methodology.html?from=grid"):
                page.write_text(nav + '<a href="' + extra + '">Scoring</a>')
                with self.assertRaisesRegex(ValueError, "Duplicate methodology links"):
                    generate.validate(root)

    def test_no_output_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "keep.txt").touch()
            with self.assertRaises(ValueError):
                generate.Site(root / "input", root)

    def test_complete_site_keeps_every_suite_and_never_publishes_markdown(self):
        import json

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input"

            def put(path, data):
                path = source / path
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.suffix == ".png":
                    Image.new("RGB", (100, 100), "white").save(path)
                    return
                path.write_text(
                    json.dumps(data) if isinstance(data, (dict, list)) else data
                )

            put("sample.zpl", "^XA^XZ")
            put("printer.png", "fixture image")
            for sid, title, comparison, corpus in generate.SUITES:
                case = {
                    "name": "sample",
                    "id": "sample",
                    "group": "shapes",
                    "zpl": "sample.zpl",
                    "source": "sample.zpl",
                    "reference": "printer.png",
                    "file": "sample.zpl",
                }
                row = {"case": "sample", "library": "go", "status": "error", "score": 0}
                put(
                    "docs/benchmarks/" + sid + "/results.json",
                    {"cases": [case], "results": [row], "measured_utc": "2000-01-01"},
                )
                if comparison:
                    reference_dir = {
                        "features": "conformance",
                        "external": "external",
                        "layout": "layout",
                    }[comparison]
                    put(
                        "benchmarks/accuracy/"
                        + reference_dir
                        + "-reference/sample.png",
                        "fixture image",
                    )
                    put(
                        "docs/benchmarks/accuracy/comparisons/"
                        + comparison
                        + "/results.json",
                        {"results": [row]},
                    )
            put(
                "docs/benchmarks/zq610-plus/results.json",
                {"cases": {}, "unavailable": {}},
            )
            put("references/zq610-plus-v1/manifest.json", {})
            put(
                "docs/benchmarks/results.json",
                {"timestamp_utc": "2000-01-01", "sizes": {}, "results": []},
            )
            for name in ("parse", "png", "generate"):
                put("docs/benchmarks/" + name + ".svg", "<svg/>")
            put(
                "docs/benchmarks/invalid/results.json",
                {"measured_utc": "2000-01-01", "cases": [], "results": []},
            )
            put("docs/benchmarks/command-support.json", {"commands": {"go": {}}})
            put(
                "docs/benchmarks/argument-support.md",
                "| Library | Text | Barcode |\n|---|---|---|\n| go | examined | partial |",
            )
            put(
                "docs/benchmarks/capabilities.md",
                "| Library | Role |\n|---|---|\n| go | renderer |",
            )
            put("docs/zpl-command-index.tsv", "^FO\t1")
            site = generate.Site(source, root / "output")
            site.generate()
            overview = (site.output / "index.html").read_text()
            self.assertIn("0.0%", overview)
            self.assertIn("1/1 scored", overview)
            self.assertIn("No observations", overview)
            self.assertEqual(len(list((site.output / "cases").glob("*.html"))), 5)
            self.assertFalse(list(site.output.rglob("*.md")))
            matrix = (site.output / "categories/accuracy.html").read_text()
            self.assertIn("comparison-matrix", matrix)
            self.assertEqual(matrix.count('<th scope="row">'), 1)
            self.assertIn("cases/accuracy--sample.html#go", matrix)
            self.assertIn("0.00% IoU", matrix)
            self.assertIn(
                "not reproducible pixel measurements",
                (site.output / "examination.html").read_text(),
            )

    def test_shared_crop_keeps_displaced_extra_ink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reference = Image.new("RGB", (832, 1218), "white")
            reference.putpixel((100, 200), (0, 0, 0))
            reference.save(root / "reference.png")
            render = Image.new("RGB", (832, 1218), "white")
            render.putpixel((350, 450), (0, 160, 220))
            render.save(root / "render.png")
            self.assertEqual(
                generate.shared_bounds([root / "reference.png", root / "render.png"]),
                (92, 192, 359, 459),
            )

    def test_crop_padding_is_white_and_original_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input"
            source.mkdir()
            image = Image.new("RGB", (12, 12), "white")
            image.putpixel((0, 0), (0, 0, 0))
            image.save(source / "image.png")
            original = (source / "image.png").read_bytes()
            site = generate.Site(source, root / "output")
            asset = site.asset("image.png")
            crop = site.focused(asset, (-8, -8, 25, 25))
            with Image.open(site.output / crop) as focused:
                self.assertEqual(focused.size, (33, 33))
                self.assertEqual(focused.getpixel((8, 8)), (0, 0, 0))
                self.assertEqual(focused.getpixel((0, 0)), (255, 255, 255))
                self.assertEqual(focused.getpixel((32, 32)), (255, 255, 255))
            self.assertEqual((site.output / asset).read_bytes(), original)

    def test_blank_crop_is_finite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "blank.png"
            Image.new("RGB", (832, 1218), "white").save(path)
            self.assertEqual(generate.shared_bounds([path]), (0, 0, 64, 64))

    def test_text_is_escaped(self):
        self.assertEqual(generate.E('<script>"'), "&lt;script&gt;&quot;")


if __name__ == "__main__":
    unittest.main()

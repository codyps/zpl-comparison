"""Publication contracts: scoring, evidence safety and navigable static output."""

import importlib.util
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from PIL import Image

spec = importlib.util.spec_from_file_location(
    "generate", Path(__file__).with_name("generate.py")
)
generate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate)


class PublicationTests(unittest.TestCase):
    def test_campaign_matrix_exposes_every_renderer_and_rejects_missing_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input"
            source.mkdir()
            for name in ["source.zpl", "reference.png", "local.png"]:
                (source / name).write_text(name)
            digest = hashlib.sha256((source / "local.png").read_bytes()).hexdigest()
            for paired in [False, True]:
                cases = [dict(name="sample-zq610" if paired else "sample", group="test", source="source.zpl", reference="reference.png")]
                if paired:
                    cases[0].update(printer="zq610", paired_case="sample")
                data = dict(schema=2, suite="paired" if paired else "public-zpl", measured_utc="recorded",
                            libraries=["go", "labelary"], manifests={}, cases=cases,
                            common_coordinate_regions={"sample": {"region": [0, 0, 2, 2]}},
                            results=[dict(case=cases[0]["name"], library="go", status="rendered", image="local.png", png_sha256=digest, score=0.5),
                                     dict(case=cases[0]["name"], library="labelary", status="error", diagnostic="HTTP error", score=None)])
                (source / "results.json").write_text(json.dumps(data))
                manifest = source / "test-data/public-zpl/manifest.json"
                manifest.parent.mkdir(parents=True, exist_ok=True)
                manifest.write_text(json.dumps({"cases": [dict(name="sample", source="https://example.org/pinned.zpl")]}))
                (manifest.parent / "sources.json").write_text("{}")
                site = generate.Site(source, root / str(paired))
                site.load_campaign_matrix(data, ".")
                self.assertEqual([r["library"] for r in site.cases[0]["rows"]], ["go", "labelary"])
                self.assertIsNone(site.cases[0]["rows"][1]["score"])
                self.assertEqual(site.cases[0]["rows"][1]["diagnostic"], "HTTP error")
                if not paired:
                    self.assertEqual(site.cases[0]["metadata"]["upstream_source"], "https://example.org/pinned.zpl")
                with self.assertRaisesRegex(ValueError, "Incomplete campaign"):
                    site.load_campaign_matrix({**data, "results": data["results"][:1]}, ".")

    def test_memory_page_identifies_protocol_and_sample_range(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            site = generate.Site(root / "input", root / "output")
            site.performance = dict(timestamp_utc="test", sizes={},
                memory=dict(warmup_operations=3, iterations=10, samples=5),
                results=[dict(library="go", mode="parse", fixture="text", status="ok",
                              median_ns=1000, peak_rss_bytes=2**20,
                              min_peak_rss_bytes=2**19, max_peak_rss_bytes=2**21)])
            rendered = []
            def capture(title, body, **kwargs):
                rendered.append(body)
                raise StopIteration
            site.write = capture
            with self.assertRaises(StopIteration):
                site.other_pages()
            self.assertIn("Median peak RSS", rendered[0])
            self.assertIn("0.50–2.00 MiB", rendered[0])
            self.assertIn("10 measured operations", rendered[0])
            self.assertIn("not per-operation allocation", rendered[0])

    def test_aztec_context_links_only_available_independent_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            s = generate.Site(root / 'input', root / 'output')
            s.page = 'cases/zq610-candidates--barcode-aztec.html'
            s.cases = [{'key': 'conformance--symbol-aztec'},
                       {'key': 'conformance--encoding-remap-identity'}]
            case = {'suite': 'zq610-candidates', 'id': 'barcode-aztec'}
            context = s.compatibility_context(case)
            self.assertIn('symbol-aztec.html', context)
            self.assertIn('encoding-remap-identity.html', context)
            self.assertNotIn('encoding-remap-control.html', context)
            self.assertIn('before reaching the barcode', context)
            self.assertEqual(s.compatibility_context({**case, 'id': 'barcode-qr'}), '')
            self.assertEqual(s.compatibility_context({**case, 'suite': 'conformance'}), '')
            for variant in ('aztec_alias', 'aztec_rune'):
                s.cases = [{'key': 'conformance--symbol-' + variant}]
                self.assertIn('symbol-' + variant + '.html', s.compatibility_context(
                    {**case, 'id': 'smoke-' + variant}))

    def test_font_variant_is_visible_and_fixed_rows_are_labeled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input"
            evidence = source / "docs/benchmarks/accuracy/results.json"
            evidence.parent.mkdir(parents=True)
            evidence.write_text(json.dumps({"results": [{"library": "labelary", "font_control": {"mode": "fixed", "note": "Service fonts cannot be replaced."}}]}))
            site = generate.Site(source, root / "controlled")
            site.write("Test", "<p>Results</p>")
            self.assertIn("Font-controlled comparison", (root / "controlled/index.html").read_text())
            self.assertIn("fonts: fixed", site.result({"status": "rendered", "font_control": {"mode": "fixed"}}))
            for label in (site.link('libraries/labelary.html', 'Labelary'), site.library_name('labelary')):
                self.assertIn('⚠', label)
                self.assertIn('aria-label="Controlled fonts unavailable; using fixed fonts.', label)
                self.assertIn('Service fonts cannot be replaced.', label)
            self.assertNotIn('⚠', site.link('libraries/zplr.html', 'ZPLr'))
            site.page = 'libraries/labelary.html'
            site.write('Labelary', '<p>Results</p>')
            self.assertIn('<h1>Labelary<span class="font-fallback"', (root / 'controlled/libraries/labelary.html').read_text())
            evidence.write_text(json.dumps({"results": [{"status": "rendered"}]}))
            default = generate.Site(source, root / "default")
            default.write("Test", "<p>Results</p>")
            self.assertNotIn("Font-controlled comparison", (root / "default/index.html").read_text())
            self.assertNotIn('⚠', default.library_name('labelary'))

    def test_performance_charts_sort_within_workload_and_exclude_failures(self):
        rows = [dict(library="go", fixture="text", status="ok", median_ns=2000000, peak_rss_bytes=2097152),
                dict(library="labelize", fixture="text", status="ok", median_ns=1000000, peak_rss_bytes=1048576),
                dict(library="forge", fixture="text", status="failed")]
        for field, divisor, unit in [("median_ns", 1e6, "ms"), ("peak_rss_bytes", 2**20, "MiB")]:
            chart = generate.performance_chart(rows, field, divisor, unit, "Comparison")
            self.assertLess(chart.index("labelize"), chart.index("go-zpl"))
            self.assertNotIn("zpl-forge", chart)
            self.assertIn("width:50.0%", chart)
            self.assertIn("1.000 " + unit, chart)
        self.assertIn("data-sortable", generate.table(["Duration"], [["1"]], "Timings", "sortable"))

    def test_public_campaign_keeps_failures_and_only_measured_library(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input"
            source.mkdir()

            def put(name, value):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value) if not isinstance(value, str) else value)
                return hashlib.sha256(path.read_bytes()).hexdigest()

            cases = [dict(name=name, group="shipping", purpose="Example", notes="Preserved",
                          commands=["^XA", "^XZ"], file=name + ".zpl", license="LICENSE")
                     for name in ["success", "failure"]]
            manifest_hash = put("test-data/public-zpl/manifest.json", {"cases": cases})
            reference_hash = put("references/public-zd621-20261002/manifest.json", {})
            put("test-data/public-zpl/sources.json", {})
            put("test-data/public-zpl/LICENSE", "MIT")
            for name in ["success", "failure"]:
                put("test-data/public-zpl/" + name + ".zpl", "^XA^XZ")
                put("references/public-zd621-20261002/" + name + ".png", "fixture")
            put("docs/public-examples/images/success.png", "fixture")
            put("docs/public-examples/images/success-diff.png", "fixture")
            data = dict(manifest_sha256=manifest_hash, reference_manifest_sha256=reference_hash,
                        measured_utc="2026-10-02", renderer=dict(revision="pinned-revision", profile="ZD621"),
                        results=[dict(case="success", library="codyps-zpl", status="rendered",
                                      comparison=dict(iou=1.0, reference_ink=1, exact=True)),
                                 dict(case="failure", library="codyps-zpl", status="error", diagnostic="unsupported Code 39 character")])
            put("docs/public-examples/results.json", data)
            site = generate.Site(source, root / "output")
            site.load_public_examples()
            self.assertEqual(len(site.cases), 2)
            self.assertEqual(site.cases[0]["rows"][0]["score"], 1.0)
            failed = site.cases[1]["rows"][0]
            self.assertIsNone(failed["score"])
            self.assertIsNone(failed["image_asset"])
            self.assertEqual(failed["diagnostic"], "unsupported Code 39 character")
            self.assertTrue(all(len(c["rows"]) == 1 for c in site.cases))
            self.assertIn("pinned-revision", site.cases[0]["notes"])
            captures = [dict(suite="public-zpl", name=c["name"]) for c in cases]
            put("docs/benchmarks/labelary/captures.json", {"cases": captures})
            image_hash = put("docs/benchmarks/labelary/images/success.png", "service fixture")
            diff_hash = put("docs/public-examples/images/success-labelary-diff.png", "difference fixture")
            service = dict(manifest_sha256=manifest_hash, reference_manifest_sha256=reference_hash,
                           captures_rows_sha256=hashlib.sha256(json.dumps(captures, sort_keys=True).encode()).hexdigest(),
                           identity="UTC timestamps; no renderer version",
                           results=[dict(case="success", library="labelary", status="rendered", received_utc="captured-time",
                                         image="docs/benchmarks/labelary/images/success.png", png_sha256=image_hash,
                                         diff="images/success-labelary-diff.png", diff_sha256=diff_hash,
                                         comparison=dict(iou=0.5, reference_ink=2)),
                                    dict(case="failure", library="labelary", status="error", received_utc="captured-time",
                                         diagnostic="HTTP error")])
            put("docs/public-examples/labelary-results.json", service)
            site = generate.Site(source, root / "service")
            site.load_public_examples()
            self.assertEqual([r["library"] for r in site.cases[0]["rows"]], ["codyps-zpl", "labelary"])
            self.assertEqual(site.cases[0]["rows"][1]["score"], 0.5)
            self.assertIsNone(site.cases[1]["rows"][1]["score"])
            self.assertIn("captured-time", site.cases[0]["notes"])
            # Unrelated service extensions must not invalidate the dated campaign.
            put("docs/benchmarks/labelary/captures.json", {"cases": captures + [dict(suite="conformance")]})
            generate.Site(source, root / "extended").load_public_examples()
            service["results"].pop()
            put("docs/public-examples/labelary-results.json", service)
            with self.assertRaisesRegex(ValueError, "Incomplete public-example Labelary"):
                generate.Site(source, root / "missing-service").load_public_examples()
            put("docs/benchmarks/labelary/captures.json", {"cases": []})
            with self.assertRaisesRegex(ValueError, "Stale public-example Labelary"):
                generate.Site(source, root / "stale-service").load_public_examples()
            data["results"].pop()
            put("docs/public-examples/results.json", data)
            with self.assertRaisesRegex(ValueError, "Incomplete public-example"):
                generate.Site(source, root / "incomplete").load_public_examples()
            put("test-data/public-zpl/manifest.json", {"cases": []})
            with self.assertRaisesRegex(ValueError, "Stale public-example"):
                generate.Site(source, root / "stale").load_public_examples()

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

    def test_variant_methodology_link_is_validated_separately(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "fonts").mkdir()
            (root / "fonts/methodology.html").write_text("<h1>Controlled methodology</h1>")
            (root / "methodology.html").write_text('<a href="methodology.html">Methodology</a><a class="variant-switch" href="fonts/methodology.html">Controlled fonts</a>')
            generate.validate(root)
            (root / "fonts/methodology.html").unlink()
            with self.assertRaisesRegex(ValueError, "Broken local link"):
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
            (source / "docs/benchmarks/results.json").unlink()
            preview = generate.Site(source, root / "preview")
            preview.generate()
            self.assertIn("this preview has no timing measurements", (preview.output / "categories/performance.html").read_text())
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

    def test_ink_bounds_preserves_opaque_and_transparent_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            for mode in ("1", "L", "RGB", "RGBA", "P"):
                for transparent in (False, True):
                    image = Image.new("RGBA", (32, 24), "white")
                    image.putpixel((10, 12), (0, 0, 0, 128 if transparent else 255))
                    image = image.convert(mode)
                    path = Path(temp) / f"{mode}-{transparent}.png"
                    options = {"transparency": (0, 0, 0) if mode == "RGB" else 0} if transparent and mode != "RGBA" else {}
                    image.save(path, **options)
                    with Image.open(path) as raw:
                        rgba = raw.convert("RGBA")
                        canvas = Image.new("RGBA", rgba.size, "white")
                        canvas.alpha_composite(rgba)
                        rgb = canvas.convert("RGB")
                        expected = generate.ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white")).getbbox()
                    self.assertEqual(generate.ink_bounds(path), expected, (mode, transparent))

    def test_preview_cache_reuses_pixels_across_output_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input"
            source.mkdir()
            image = Image.new("RGBA", (32, 24), (255, 255, 255, 0))
            image.putpixel((10, 12), (0, 0, 0, 255))
            image.save(source / "image.png")
            cache = generate.PreviewCache(root / "cache")
            first = generate.Site(source, root / "first", cache)
            asset = first.asset("image.png")
            bounds = cache.frame(first.output, [asset])
            self.assertEqual(bounds, generate.shared_bounds([first.output / asset]))
            preview = first.focused(asset, bounds)
            expected = (first.output / preview).read_bytes()
            self.assertEqual(expected, generate.crop_png(first.output / asset, bounds))
            cache.save()
            restored = generate.PreviewCache(root / "cache")
            second = generate.Site(source, root / "second", restored)
            second_asset = second.asset("image.png")
            with patch.object(generate, "crop_png", side_effect=AssertionError("Unexpected crop")), \
                 patch.object(generate, "ink_bounds", side_effect=AssertionError("Unexpected decode")):
                self.assertEqual(restored.frame(second.output, [second_asset]), bounds)
                self.assertEqual(second.focused(second_asset, bounds), preview)
            self.assertEqual((second.output / preview).read_bytes(), expected)
            self.assertEqual(restored.hits, 1)
            # Crop geometry is an input, even when the source PNG is identical.
            second.focused(second_asset, (0, 0, 32, 24))
            self.assertEqual(restored.misses, 1)
            # Damaged entries are rebuilt, never published under a false digest.
            (restored.root / Path(preview).name).write_bytes(b"damaged")
            third = generate.Site(source, root / "third", restored)
            self.assertEqual(third.focused(third.asset("image.png"), bounds), preview)
            self.assertEqual((third.output / preview).read_bytes(), expected)
            with patch.object(generate, "PREVIEW_CACHE_VERSION", 999):
                self.assertEqual(generate.PreviewCache(root / "cache").images, {})

    def test_text_is_escaped(self):
        self.assertEqual(generate.E('<script>"'), "&lt;script&gt;&quot;")


if __name__ == "__main__":
    unittest.main()

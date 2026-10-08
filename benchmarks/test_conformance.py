"""Corpus determinism, rendering-only scope, counted data, and honest oracles."""

import importlib.util
import hashlib
import json
import io
import re
import urllib.error
from unittest.mock import patch
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
    def test_font_selectors_and_graphic_symbols_remain_covered(self):
        cases = generator.rows()
        selectors = set()
        for case in cases:
            if case['group'] == 'fonts':
                selectors.update(re.findall(rb'\^A([0-9A-Z])[NRIB],', case['zpl']))
        self.assertEqual(selectors, {bytes([c]) for c in b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'})
        symbols = {match for case in cases for match in re.findall(
            rb'\^GS([NRIB]),48,48\^FD([A-E])\^FS', case['zpl'])}
        self.assertEqual(symbols, {(o.encode(), s.encode()) for o in 'NRIB' for s in 'ABCDE'})

    def test_every_zd621_rom_font_has_a_named_comparison(self):
        evidence = ROOT.parent / "references/zd621-fonts-20261008"
        inventory = json.loads((evidence / "inventory.json").read_text())
        directory = (evidence / "directory.html").read_bytes()
        self.assertEqual(hashlib.sha256(directory).hexdigest(), inventory["directory_sha256"])
        fonts = set(re.findall(rb'<TD ALIGN="LEFT">(Z:[^<]+\.(?:FNT|TTF|TTE))</TD>', directory))
        self.assertEqual(fonts, {font.encode() for font in inventory["fonts"]})
        self.assertEqual(len(fonts), 78)
        all_directory = (evidence / "directory-all.html").read_bytes()
        self.assertEqual(hashlib.sha256(all_directory).hexdigest(), inventory["all_directory_sha256"])
        fonts = set(re.findall(rb'<TD ALIGN="LEFT">([^<]+\.(?:FNT|TTF|TTE))</TD>', all_directory))
        self.assertEqual(fonts, {f.encode() for f in inventory['fonts'] + inventory['user_fonts']})
        cases = [c for c in generator.rows() if c['group'] in {'fonts-rom', 'fonts-installed'}]
        self.assertEqual(len(cases), len(fonts))
        covered = set()
        for case in cases:
            names = re.findall(rb'\^A@N,(?:0,0|32,24),([EZ]:[^^]+)\^FD', case['zpl'])
            self.assertEqual(len(names), 2, case['name'])
            self.assertEqual(names[0], names[1])
            covered.add(names[0])
            self.assertIn('^A@', case['commands'])
        self.assertEqual(covered, fonts)
        probes = capture.corpus_probes(SUITE, ['fonts-rom', 'fonts-installed'])
        self.assertEqual({p['name'] for p in probes}, {c['name'] for c in cases} | {'repeat-end'})

    def test_rom_fonts_have_printer_and_labelary_evidence(self):
        _, cases = conformance.load_cases(SUITE, groups=['fonts-rom', 'fonts-installed'])
        evidence = ROOT.parent / 'references/zd621-fonts-20261008/capture'
        captured = {}
        for directory, group in [(evidence, 'fonts-rom'), (evidence.parent / 'installed-capture', 'fonts-installed')]:
            capture_manifest, _ = conformance.reference_images(directory, [c for c in cases if c['group'] == group])
            self.assertEqual(capture_manifest['device'], 'ZTC ZD621-203dpi ZPL')
            self.assertEqual(capture_manifest['failures'], [])
            captured.update({r['name']: r for r in capture_manifest['cases']})
        references, _ = conformance.reference_images(ROOT / 'accuracy/conformance-reference', cases)
        saved = {r['name']: r for r in references['cases']}
        labelary_root = ROOT.parent / 'docs/benchmarks/labelary'
        labelary = json.loads((labelary_root / 'captures.json').read_text())
        responses = {r['name']: r for r in labelary['cases'] if r['suite'] == 'conformance'}
        for case in cases:
            name = case['name']
            with self.subTest(name=name):
                self.assertEqual(saved[name]['png_sha256'], captured[name]['png_sha256'])
                row = responses[name]
                self.assertEqual(row['sha256'], case['sha256'])
                self.assertEqual(row['status'], 'rendered')
                self.assertEqual(row['dimensions'], [case['width'], case['height']])
                self.assertEqual(conformance.metrics.sha(labelary_root / row['image']), row['png_sha256'])
                printer = conformance.metrics.gray(ROOT / 'accuracy/conformance-reference' / (name + '.png'))
                self.assertEqual(not np.any(printer < 128), bool(case.get('reference_unscored_reason')))

    def test_aztec_and_ci_remapping_are_independent(self):
        cases = {c['name']: c for c in generator.rows()}
        for variant in ('aztec', 'aztec_alias', 'aztec_rune'):
            data = cases['symbol-' + variant]['zpl']
            self.assertNotRegex(data, rb'\^CI\d+,')
            self.assertRegex(data, rb'\^B[O0]')
        control = cases['encoding-remap-control']
        identity = cases['encoding-remap-identity']
        self.assertIn(b'^CI0,0,0', identity['zpl'])
        self.assertEqual(identity['zpl'].replace(b'^CI0,0,0', b'^CI0'), control['zpl'])
        self.assertEqual(identity['relation'], control['relation'])
        self.assertNotRegex(identity['zpl'], rb'\^B[O0]')
        self.assertIn(b'^CI0,65,66', cases['encoding-remap']['zpl'])

    def test_native_preview_migration_isolates_rounding(self):
        regular = {c['name']: c for c in generator.rows()}
        native = {c['name']: c for c in generator.rows(native_preview=True)}
        for name, case in regular.items():
            self.assertEqual(case['width'] % 64, 0, name)
            self.assertEqual(case['zpl'], native[name]['zpl'])
            if case['group'] == 'barcode-families':
                self.assertEqual(case['width'], 832)
                self.assertEqual(case['zpl'], (ROOT.parent / case['source']).read_bytes())
        low, high = (native[f'preview-width-{w}'] for w in (812, 832))
        self.assertEqual(low['zpl'].replace(b'^PW812', b'^PW832'), high['zpl'])
        self.assertEqual(low['group'], 'preview-width-rounding')
        self.assertNotIn(b'^FD', low['zpl'])
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for name, data in generator.artifacts(list(native.values())).items():
                path = dest / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            probes = capture.corpus_probes(dest, groups=['preview-width-rounding'])
            self.assertEqual([p['width'] for p in probes], [812, 832, 812])

    def test_font_free_layout_corpus(self):
        directory = SUITE.parent / "layout-accuracy"
        layout = module("layout_generator", directory / "generate.py")
        for filename, data in layout.artifacts().items():
            if filename != "COVERAGE.md":
                self.assertEqual((directory / filename).read_bytes(), data, filename)
        _, cases = conformance.load_cases(directory)
        self.assertEqual(len(cases), 20)
        for case in cases:
            data = case["path"].read_bytes()
            self.assertNotIn("^A", case["commands"])
            self.assertNotIn("^CF", case["commands"])
            if "^FD" in case["commands"]:
                # Barcode data is permitted only with both caption flags off.
                self.assertIn(b"^BC,40,N,N,N,N^FDAB12^FS", data)
            else:
                self.assertIn("^GB", case["commands"])
        probes = capture.corpus_probes(directory)
        self.assertEqual(probes[0]["zpl"], probes[-1]["zpl"])
        reference, images = conformance.reference_images(
            ROOT / "accuracy/layout-reference", cases
        )
        self.assertEqual(reference["corpus_sha256"], conformance.metrics.sha(directory / "manifest.json"))
        self.assertEqual(set(images), {case["name"] for case in cases})
        self.assertTrue(all(np.any(image < 128) for image in images.values()))
        self.assertTrue(np.array_equal(images["layout-home"], images["layout-home-direct"]))

    def test_missing_adapter_fails_preflight(self):
        with self.assertRaisesRegex(ValueError, "Missing adapter executable"):
            conformance.metrics.preflight(
                {"commands": {"forge": ["/does-not-exist/forge"]}}, ["forge"]
            )
        with self.assertRaisesRegex(ValueError, "Missing FFI native library"):
            conformance.metrics.preflight(
                {"commands": {"ffi": [sys.executable]}}, ["ffi"]
            )

    def test_capture_records_missing_preview_and_still_checks_control(self):
        png = io.BytesIO()
        Image.new("L", (2, 2), 0).save(png, format="PNG")
        probes = [
            dict(name=name, zpl=b"^XA^BY3,2,100^FO0,0^FDtest^FS^XZ")
            for name in ["first", "missing", "repeat-end"]
        ]
        replies = iter(
            [
                b"ZTC ZD621-203dpi ZPL<",
                b"V93.21.33Z FIRMWARE",
                b'<IMG SRC="/first.png">',
                png.getvalue(),
                b'<IMG SRC="/missing.png">',
                urllib.error.HTTPError(
                    "http://printer/missing.png", 404, "Not Found", {}, None
                ),
                b'<IMG SRC="/last.png">',
                png.getvalue(),
            ]
        )

        def open_response(request, timeout):
            self.assertNotIn(b"Print+Label", request.data or b"")
            if request.data:
                form = capture.urllib.parse.parse_qs(request.data.decode())
                self.assertEqual(form["oname"], ["CMPACC"])
                self.assertEqual(form["data"][0].count("^XA"), 1)
                self.assertEqual(form["data"][0].count("^XZ"), 1)
                self.assertIn("^PMN", form["data"][0])
                self.assertIn("^BY2,3,10^", form["data"][0])
                self.assertNotIn("^BY2,3,100^", form["data"][0])
                identity = ",".join(f"{value},{value}" for value in range(256))
                for encoding in (0, 13):
                    self.assertIn(f"^CI{encoding},{identity}^", form["data"][0])
                self.assertLess(
                    form["data"][0].index("^BY2,3,10^"),
                    form["data"][0].index("^BY3,2,100^"),
                )
            result = next(replies)
            if isinstance(result, Exception):
                raise result
            return io.BytesIO(result)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "capture"
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "capture.py",
                        "--host",
                        "http://printer",
                        "--output",
                        str(output),
                        "--interval",
                        "0",
                    ],
                ),
                patch.object(capture, "probes", return_value=probes),
                patch.object(capture.urllib.request, "build_opener") as build,
            ):
                build.return_value.open.side_effect = open_response
                capture.main()
            data = json.loads((output / "manifest.json").read_text())
            self.assertEqual(data["status"], "complete")
            self.assertTrue(data["repeat_pixels_equal"])
            self.assertEqual([r["name"] for r in data["failures"]], ["missing"])
            self.assertFalse((output / "missing.png").exists())

    def test_timeout_waits_for_recovery_without_replaying_post(self):
        png = io.BytesIO()
        Image.new("L", (2, 2), 0).save(png, format="PNG")
        probes = [
            dict(name=name, zpl=b"^XA^FDtest^FS^XZ")
            for name in ["first", "slow", "repeat-end"]
        ]
        replies = iter(
            [
                b"ZTC ZD621-203dpi ZPL<",
                b"V93.21.33Z FIRMWARE",
                b'<IMG SRC="/first.png">',
                png.getvalue(),
                TimeoutError("busy"),
                b"recovered",
                b'<IMG SRC="/last.png">',
                png.getvalue(),
            ]
        )
        posts = []

        def respond(request, timeout):
            if request.data:
                posts.append(request.data)
            reply = next(replies)
            if isinstance(reply, Exception):
                raise reply
            return io.BytesIO(reply)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "capture"
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "capture.py",
                        "--host",
                        "http://printer",
                        "--output",
                        str(output),
                        "--interval",
                        "0",
                    ],
                ),
                patch.object(capture, "probes", return_value=probes),
                patch.object(capture.urllib.request, "build_opener") as build,
                patch.object(capture.time, "sleep") as sleep,
            ):
                build.return_value.open.side_effect = respond
                capture.main()
            sleep.assert_any_call(30)
            self.assertEqual(len(posts), 3)
            data = json.loads((output / "manifest.json").read_text())
            self.assertEqual(data["status"], "complete")
            self.assertEqual(data["failures"][0]["name"], "slow")
            self.assertIn("not replayed", data["failures"][0]["error"])

    def test_unrecovered_timeout_preserves_failure_for_resume(self):
        png = io.BytesIO()
        Image.new("L", (2, 2), 0).save(png, format="PNG")
        probes = [
            dict(name=name, zpl=b"^XA^FDtest^FS^XZ")
            for name in ["first", "slow", "repeat-end"]
        ]
        replies = iter(
            [
                b"ZTC ZD621-203dpi ZPL<",
                b"V93.21.33Z FIRMWARE",
                b'<IMG SRC="/first.png">',
                png.getvalue(),
                TimeoutError("busy"),
                TimeoutError("still busy"),
            ]
        )

        def respond(request, timeout):
            reply = next(replies)
            if isinstance(reply, Exception):
                raise reply
            return io.BytesIO(reply)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "capture"
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "capture.py",
                        "--host",
                        "http://printer",
                        "--output",
                        str(output),
                        "--interval",
                        "0",
                        "--recovery-attempts",
                        "1",
                    ],
                ),
                patch.object(capture, "probes", return_value=probes),
                patch.object(capture.urllib.request, "build_opener") as build,
                patch.object(capture.time, "sleep"),
            ):
                build.return_value.open.side_effect = respond
                with self.assertRaisesRegex(TimeoutError, "remains resumable"):
                    capture.main()
            data = json.loads((output / "manifest.json").read_text())
            self.assertEqual(data["status"], "incomplete")
            self.assertEqual(data["failures"][0]["name"], "slow")
            self.assertTrue((output / "slow.zpl").exists())
            self.assertFalse((output / "repeat-end.png").exists())

    def test_literal_nul_fixture_is_not_submitted(self):
        png = io.BytesIO()
        Image.new("L", (2, 2), 0).save(png, format="PNG")
        probes = [
            dict(name="first", zpl=b"^XA^FDtest^FS^XZ"),
            dict(name="binary", zpl=b"^XA^GFB,1,1,1,\x00^FS^XZ"),
            dict(name="repeat-end", zpl=b"^XA^FDtest^FS^XZ"),
        ]
        replies = iter(
            [
                b"ZTC ZD621-203dpi ZPL<",
                b"V93.21.33Z FIRMWARE",
                b'<IMG SRC="/first.png">',
                png.getvalue(),
                b'<IMG SRC="/last.png">',
                png.getvalue(),
            ]
        )
        posts = []

        def respond(request, timeout):
            if request.data:
                posts.append(request.data)
                self.assertNotIn(b"%00", request.data)
            return io.BytesIO(next(replies))

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "capture"
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "capture.py",
                        "--host",
                        "http://printer",
                        "--output",
                        str(output),
                        "--interval",
                        "0",
                    ],
                ),
                patch.object(capture, "probes", return_value=probes),
                patch.object(capture.urllib.request, "build_opener") as build,
            ):
                build.return_value.open.side_effect = respond
                capture.main()
            data = json.loads((output / "manifest.json").read_text())
            self.assertEqual(len(posts), 2)
            self.assertEqual(data["status"], "complete")
            self.assertIn("NUL", data["failures"][0]["error"])
            self.assertIn(b"\x00", (output / "binary.zpl").read_bytes())

    def test_external_examples_are_pinned_and_capture_scope_is_separate(self):
        directory = ROOT.parent / "test-data/external-zpl"
        manifest, cases = conformance.load_cases(directory)
        self.assertEqual(len(cases), 9)
        self.assertEqual(len({c["name"] for c in cases}), 9)
        for source in manifest["sources"]:
            self.assertEqual(
                conformance.metrics.sha(directory / source["license"]),
                source["license_sha256"],
            )
        for case in cases:
            self.assertIn(case["revision"], case["source"])
            self.assertTrue((directory / case["license"]).is_file())
        shipping = next(c for c in cases if c["name"] == "zpl-toolchain-shipping_label")
        original = directory / shipping["derived_from"]["file"]
        self.assertEqual(conformance.metrics.sha(original), shipping["derived_from"]["sha256"])
        self.assertEqual(shipping["path"].read_bytes(), original.read_bytes().replace(b"^PW812", b"^PW832"))
        self.assertEqual(shipping["width"], 832)
        probes = capture.corpus_probes(directory)
        self.assertEqual(len(probes), 10)  # Nine examples plus repeated control.
        for case in cases:
            self.assertEqual(case["width"] % 64, 0)
            self.assertLessEqual(case["width"], 832)
            self.assertIn(f"^PW{case['width']}".encode(), case["path"].read_bytes())
        for group in ["stateful", "printer-configuration"]:
            self.assertEqual(len(capture.corpus_probes(directory, [group])), 2)
        _, images = conformance.reference_images(ROOT / "accuracy/external-reference", cases)
        self.assertEqual(len(images), 8)
        for case in cases:
            if case.get("reference_unscored_reason"):
                self.assertNotIn(case["name"], images)
            else:
                self.assertEqual(images[case["name"]].shape, (case["height"], case["width"]))
        retail = next(c for c in cases if c["name"] == "zplr-retail-upc-ean")
        utf8 = next(c for c in cases if c["name"] == "zplr-retail-upc-ean-utf8")
        self.assertNotIn(b"^CI", retail["path"].read_bytes())
        self.assertEqual(utf8["path"].read_bytes(), retail["path"].read_bytes().replace(b"^XA\n", b"^XA\n^CI28\n", 1))
        self.assertIn(utf8["name"], images)
        with self.assertRaisesRegex(ValueError, "Reference belongs to different input"):
            conformance.reference_images(ROOT / "accuracy/external-reference", [dict(retail, sha256="0" * 64)])

    def test_ram_capture_scope_is_limited_to_reviewed_resources(self):
        _, cases = conformance.load_cases(SUITE.parent / "external-zpl")
        case = next(c for c in cases if c["group"] == "stateful")
        source = case["path"].read_bytes()
        capture.validate_capture_source(source, case, generator)
        for unsafe in [source.replace(b"R:CMPEX", b"E:CMPEX"), source + b"~JA", source.replace(b",16,2,", b",32,2,")]:
            with self.assertRaises(ValueError):
                capture.validate_capture_source(unsafe, case, generator)

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
            manifest["preview_reset_zpl"] = "^XA^PMN^XZ"
            for row in rows:
                source = (directory / (row["name"] + ".zpl")).read_bytes()
                row.update(
                    submission_mode="inline-reset",
                    submitted_sha256=capture.sha(source[:3] + b"^PMN" + source[3:]),
                )
            path.write_text(json.dumps(manifest))
            conformance.reference_images(directory, cases)
            saved_hash = rows[0]["submitted_sha256"]
            rows[0]["submitted_sha256"] = "wrong"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Submitted preview hash"):
                conformance.reference_images(directory, cases)
            rows[0]["submitted_sha256"] = saved_hash
            path.write_text(json.dumps(manifest))
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
        self.assertIn('^A@', generator.commands(b'^XA^A@N,32,24,Z:TT0003M_.TTF^FDTest^FS^XZ'))
        for forbidden in [b"^XF", b"^DF", b"^PQ", b"^MD", b"^JUS", b"^RF"]:
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
        results = {("codyps-zpl", n): {"status": "blank"} for n in ["a", "b"]}
        self.assertEqual(
            conformance.relations(cases, results, {}, ["codyps-zpl"])[0]["status"],
            "inconclusive",
        )
        for r in results.values():
            r["status"] = "rendered"
        images = {
            ("codyps-zpl", "a"): np.array([[0, 255]]),
            ("codyps-zpl", "b"): np.array([[0, 255]]),
        }
        self.assertEqual(
            conformance.relations(cases, results, images, ["codyps-zpl"])[0]["status"],
            "equal",
        )
        images[("codyps-zpl", "b")] = np.array([[255, 0]])
        self.assertEqual(
            conformance.relations(cases, results, images, ["codyps-zpl"])[0]["status"],
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

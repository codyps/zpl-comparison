"""Behavioral tests for independently cached actions and optional image outputs."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from benchmarks.accuracy.pixels import gray, sha
from benchmarks.accuracy.presentation import rgb
from benchmarks.accuracy.metrics import compare
from build.compare import comparison, save_difference
from build.check_action_graph import LAYOUT_LIBRARIES, verify_layout_matrix
from build.pages import write
from build.render import render
from build.saved import saved
from build.aggregate import aggregate
from build.stage import stage
from benchmarks import refresh_candidates


class PipelineTest(unittest.TestCase):
    def test_missing_or_changed_baseline_is_unscored(self):
        expected = dict(source_sha256=sha(self.source), requested_dimensions=[2, 2],
                        render_profile="zd621-203dpi", input_identity="current-adapter", timeout_seconds=45)
        evidence = self.root / "evidence.json"
        matching = dict(expected, case="new-case", library="example", status="rendered",
                        render_sha256=sha(self.reference), observed_utc="2026-10-02T00:00:00Z")
        variants = [None] + [dict(matching, **{key: "changed"}) for key in expected]
        for index, value in enumerate(variants):
            if value:
                evidence.write_text(json.dumps(value))
            row, images = self.root / f"row{index}.json", self.root / f"images{index}"
            saved(dict(row=dict(case="new-case", library="example"), expected=expected,
                       evidence=str(evidence) if value else None, image=str(self.reference)), row, images)
            self.assertEqual(json.loads(row.read_text())["status"], "not_captured")
            self.assertFalse(list(images.iterdir()))
            scored = self.root / f"score{index}.json"
            comparison(dict(suite="accuracy", row=str(row), image=str(images),
                            reference=str(self.reference), sha256=sha(self.reference)), scored, self.root / f"diff{index}")
            self.assertIsNone(json.loads(scored.read_text())["score"])

    def test_compatible_baseline_preserves_evidence_and_rejects_corruption(self):
        expected = dict(source_sha256=sha(self.source), requested_dimensions=[2, 2],
                        render_profile="zd621-203dpi", input_identity="current-adapter", timeout_seconds=45)
        evidence = self.root / "evidence.json"
        row = dict(expected, case="case", library="example", status="rendered",
                   render_sha256=sha(self.reference), observed_utc="2026-10-02T00:00:00Z",
                   adapter_identity_sha256="recorded-deployment")
        evidence.write_text(json.dumps(row))
        spec = dict(row=dict(case="case", library="example"), expected=expected,
                    evidence=str(evidence), image=str(self.reference))
        saved(spec, self.root / "row.json", self.root / "images")
        self.assertEqual(json.loads((self.root / "row.json").read_text()), dict(row, evidence_mode="saved"))
        self.assertEqual(sha(self.root / "images/image.png"), sha(self.reference))
        evidence.write_text(json.dumps(dict(row, iou=0.9, reference_ink=20, comparison={"exact": True})))
        saved(spec, self.root / "row.json", self.root / "images")
        replay = json.loads((self.root / "row.json").read_text())
        self.assertNotIn("iou", replay)
        self.assertNotIn("comparison", replay)
        self.assertNotIn("reference_ink", replay)
        self.reference.write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            saved(spec, self.root / "bad.json", self.root / "bad-images")

    def test_render_profile_is_explicit_and_does_not_leak_from_environment(self):
        library = self.root / "library"
        library.mkdir()
        (library / "command.json").write_text('["adapter"]')
        spec = self.spec()
        spec.pop("saved")
        spec["library"] = str(library)

        def execute(command, **kwargs):
            self.assertEqual(kwargs["env"]["ZPL_RENDER_PROFILE"], expected)
            Image.new("L", (2, 2), 0).save(command[4])
            return subprocess.CompletedProcess(command, 0, b"", b"")

        with patch.dict(os.environ, {"ZPL_RENDER_PROFILE": "ambient-invalid"}):
            for expected in ("zd621-203dpi", "zq610-plus-203dpi"):
                if expected == "zq610-plus-203dpi":
                    spec["render_profile"] = expected
                with patch("build.render.subprocess.run", side_effect=execute):
                    render(spec, self.root / "result.json", self.root / expected)
                self.assertEqual(json.loads((self.root / "result.json").read_text())["status"], "rendered")

    def test_selective_refresh_preserves_other_library_evidence(self):
        folder = self.root / "docs/benchmarks/accuracy"
        images = folder / "images"
        images.mkdir(parents=True)
        untouched = b"unrelated saved bytes"
        (images / "one-other.png").write_bytes(untouched)
        library = self.root / "bazel-bin/library_example"
        library.mkdir(parents=True)
        (library / "identity.json").write_text("[]")
        (self.root / "benchmarks").mkdir()
        (self.root / "benchmarks/sources.lock.json").write_text("{}")
        other = dict(case="one", library="other", status="rendered", observed_utc="original")
        data = dict(cases=[dict(id="one", name="one", group="test", width=2, height=2,
                               zpl="case.zpl", zpl_sha256=sha(self.source),
                               reference="printer.png", png_sha256=sha(self.reference))],
                    results=[dict(case="one", library="example", status="error"), other])
        target = folder / "results.json"
        target.write_text(json.dumps(data))
        def saved_render(spec, metadata, output):
            render({**spec, "saved": str(self.reference), "png_sha256": sha(self.reference)}, metadata, output)
        with patch.object(refresh_candidates, "ROOT", self.root), patch.object(refresh_candidates, "render", side_effect=saved_render):
            refresh_candidates.refresh("accuracy", ["example"], self.root / "work", save=True)
        result = json.loads(target.read_text())
        self.assertEqual(result["results"][1], other)
        self.assertEqual((images / "one-other.png").read_bytes(), untouched)
        self.assertTrue(result["results"][0]["exact"])
        self.assertEqual(result["refreshes"][0]["libraries"], ["example"])

    def test_native_canvas_mismatch_is_unscored_and_never_padded(self):
        images = self.root / "native-images"
        images.mkdir()
        Image.new("L", (3, 2), 255).save(images / "image.png")
        row = self.root / "native-row.json"
        row.write_text(json.dumps({"status": "rendered", "render_sha256": sha(images / "image.png")}))
        result = self.root / "native-result.json"
        diff = self.root / "native-diff"
        comparison({"suite": "zq610", "row": str(row), "image": str(images),
                    "reference": str(self.reference), "sha256": sha(self.reference),
                    "strict_native_canvas": True}, result, diff)
        metrics = json.loads(result.read_text())
        self.assertEqual(metrics["comparison_status"], "canvas_mismatch")
        self.assertIsNone(metrics["score"])
        self.assertFalse(metrics["exact"])
        self.assertEqual(list(diff.iterdir()), [])
        Image.new("L", (2, 2), 255).save(images / "image.png")
        with self.assertRaisesRegex(ValueError, "Candidate render hash mismatch"):
            comparison({"suite": "zq610", "row": str(row), "image": str(images),
                        "reference": str(self.reference), "sha256": sha(self.reference),
                        "strict_native_canvas": True}, result, diff)

    def test_saved_import_preserves_bytes_and_failure_evidence(self):
        row = {"case": "one", "library": "example", "status": "rendered", "raw_png_sha256": "original"}
        saved({"row": row, "image": str(self.reference)}, self.root / "row", self.root / "images")
        self.assertEqual((self.root / "images/image.png").read_bytes(), self.reference.read_bytes())
        self.assertEqual(json.loads((self.root / "row").read_text()), row)
        failure = {**row, "status": "timeout", "diagnostic": "saved timeout"}
        saved({"row": failure}, self.root / "failed-row", self.root / "failed-images")
        self.assertEqual(list((self.root / "failed-images").iterdir()), [])
        self.assertEqual(json.loads((self.root / "failed-row").read_text()), failure)
        with self.assertRaises(FileNotFoundError):
            saved({"row": row, "image": str(self.root / "missing.png")}, self.root / "missing-row", self.root / "missing-images")

    def test_saved_aggregate_preserves_measurement_provenance(self):
        row = self.root / "row.json"
        row.write_text(json.dumps({"case": "one", "status": "rendered"}))
        provenance = {"host": {"machine": "original"}, "adapters": {"example": {"revision": "saved"}}, "measured_utc": "2020-01-01T00:00:00Z"}
        aggregate({"metadata": {}, "cases": [], "rows": [str(row)], "suite": "accuracy", "captured_utc": provenance["measured_utc"], "libraries": {}, "saved_provenance": provenance, "renders": "results"}, self.root / "aggregate")
        result = json.loads((self.root / "aggregate/results/results.json").read_text())
        for key, value in provenance.items():
            self.assertEqual(result[key], value)
        self.assertIn("saved renderer", result["generation"])

    def test_replay_keeps_adapter_identity_only_for_compatible_observations(self):
        rows = []
        for library, mode in [("measured", "saved"), ("changed", "unavailable")]:
            path = self.root / (library + ".json")
            path.write_text(json.dumps(dict(library=library, evidence_mode=mode,
                                           observed_utc="2020-01-01T00:00:00Z" if mode == "saved" else "unavailable")))
            rows.append(str(path))
        identities = self.root / "adapters.json"
        identities.write_text(json.dumps({name: dict(revision="original") for name in ["measured", "changed"]}))
        aggregate(dict(metadata={}, cases=[], rows=rows, suite="accuracy", libraries={},
                       saved_adapters=str(identities), saved_provenance=dict(host="Saved observations"),
                       renders="results"), self.root / "aggregate")
        result = json.loads((self.root / "aggregate/results/results.json").read_text())
        self.assertEqual(result["adapters"], dict(measured=dict(revision="original")))
        self.assertEqual(result["measured_utc"], "2020-01-01T00:00:00Z")

    def test_layout_matrix_requires_every_renderer_and_printer_comparison(self):
        cases = ["layout-control", "layout-home"]
        complete = [f"{case}-{lib}" for case in cases for lib in LAYOUT_LIBRARIES]
        verify_layout_matrix(complete, complete, cases)
        for renders, comparisons in [(complete[:-1], complete), (complete, complete[:-1]), (complete, complete + complete[:1])]:
            with self.assertRaisesRegex(AssertionError, "Incomplete font-free layout"):
                verify_layout_matrix(renders, comparisons, cases)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "case.zpl"
        self.source.write_text("^XA^XZ")
        self.reference = self.root / "printer.png"
        Image.fromarray(np.array([[0, 255], [255, 255]], dtype=np.uint8)).save(
            self.reference
        )

    def spec(self):
        return {
            "source": str(self.source),
            "sha256": sha(self.source),
            "width": 2,
            "height": 2,
            "row": {
                "case": "one",
                "library": "example",
                "group": "test",
                "status": "rendered",
            },
            "saved": str(self.reference),
            "png_sha256": sha(self.reference),
        }

    def test_saved_render_comparison_and_optional_assembly(self):
        row, image = self.root / "render.json", self.root / "render"
        render(self.spec(), row, image)
        scored, diff = self.root / "scored.json", self.root / "diff"
        comparison(
            {
                "suite": "accuracy",
                "row": str(row),
                "image": str(image),
                "reference": str(self.reference),
                "sha256": sha(self.reference),
            },
            scored,
            diff,
        )
        result = json.loads(scored.read_text())
        self.assertTrue(result["exact"])
        self.assertEqual(result["score"], 1)
        stage(
            {
                "inputs": [
                    [str(image), "docs/render.png"],
                    [str(diff), "docs/diff.png"],
                ],
                "assemble": True,
            },
            self.root / "assembled",
        )
        self.assertTrue((self.root / "assembled/docs/render.png").is_file())
        self.assertFalse((self.root / "assembled/docs/render.png/image.png").exists())
        self.assertEqual(sha(self.reference), self.spec()["png_sha256"])

    def test_error_has_no_image_and_scores_zero(self):
        spec = self.spec()
        spec.update(
            saved="",
            row={**spec["row"], "status": "error", "diagnostic": "unsupported"},
        )
        row, image = self.root / "render.json", self.root / "render"
        render(spec, row, image)
        scored, diff = self.root / "scored.json", self.root / "diff"
        comparison(
            {
                "suite": "accuracy",
                "row": str(row),
                "image": str(image),
                "reference": str(self.reference),
                "sha256": sha(self.reference),
            },
            scored,
            diff,
        )
        self.assertEqual(json.loads(scored.read_text())["score"], 0)
        self.assertEqual(list(image.iterdir()), [])
        self.assertEqual(list(diff.iterdir()), [])
        stage(
            {"inputs": [[str(image), "missing.png"]], "assemble": True},
            self.root / "assembled",
        )
        self.assertFalse((self.root / "assembled/missing.png").exists())

    def test_changed_source_and_capture_are_rejected(self):
        spec = self.spec()
        self.source.write_text("changed")
        with self.assertRaisesRegex(ValueError, "Input hash mismatch"):
            render(spec, self.root / "row", self.root / "image")
        spec = self.spec()
        spec["png_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "capture hash mismatch"):
            render(spec, self.root / "row", self.root / "image")

    def test_local_command_runs_and_nonzero_is_not_a_blank(self):
        library = self.root / "library"
        library.mkdir()
        script = library / "adapter.py"
        script.write_text(
            "import sys; print('unsupported input', file=sys.stderr); sys.exit(7)"
        )
        (library / "command.json").write_text(
            json.dumps([sys.executable, "adapter.py"])
        )
        spec = self.spec()
        del spec["saved"]
        spec["library"] = str(library)
        render(spec, self.root / "row", self.root / "images")
        row = json.loads((self.root / "row").read_text())
        self.assertEqual(row["status"], "error")
        self.assertEqual(row["returncode"], 7)
        self.assertIn("unsupported input", row["diagnostic"])
        self.assertFalse((self.root / "images/image.png").exists())

    def test_successful_render_encodes_once_and_preserves_raw_identity(self):
        library = self.root / "library"
        library.mkdir()
        (library / "adapter.py").write_text(
            "import shutil, sys\n"
            f"shutil.copyfile({str(self.reference)!r}, sys.argv[4])\n"
        )
        (library / "command.json").write_text(json.dumps([sys.executable, "adapter.py"]))
        spec = self.spec()
        del spec["saved"]
        spec["library"] = str(library)
        save = Image.Image.save
        with patch.object(Image.Image, "save", autospec=True, side_effect=save) as calls:
            render(spec, self.root / "row", self.root / "images")
        self.assertEqual(calls.call_count, 1)
        row = json.loads((self.root / "row").read_text())
        self.assertEqual(row["raw_png_sha256"], sha(self.reference))
        np.testing.assert_array_equal(gray(self.root / "images/image.png"), gray(self.reference))

    def test_palette_difference_preserves_every_color_and_canvas(self):
        ref = np.array([[0, 0, 255, 255]], dtype=np.uint8)
        out = np.array([[0, 255, 0, 255], [0, 255, 255, 255]], dtype=np.uint8)
        _, diff = compare(ref, out)
        path = self.root / "diff.png"
        save_difference(diff, path)
        with Image.open(path) as saved:
            self.assertEqual(saved.mode, "P")
            self.assertEqual(saved.size, (4, 2))
            np.testing.assert_array_equal(np.asarray(saved.convert("RGB")), diff)

    def test_fast_decoding_preserves_white_compositing(self):
        for mode in ["L", "RGB", "RGBA", "P"]:
            for transparent in [False, True]:
                with self.subTest(mode=mode, transparent=transparent):
                    im = Image.new("RGBA", (3, 2), (20, 60, 120, 100)).convert(mode)
                    path = self.root / "input.png"
                    options = {}
                    if transparent and mode != "RGBA":
                        options["transparency"] = im.getpixel((0, 0))
                    im.save(path, **options)
                    with Image.open(path) as source:
                        rgba = source.convert("RGBA")
                        white = Image.new("RGBA", source.size, "white")
                        white.alpha_composite(rgba)
                        expected = white.convert("RGB")
                    np.testing.assert_array_equal(np.asarray(rgb(path)), np.asarray(expected))
                    np.testing.assert_array_equal(gray(path), np.asarray(expected.convert("L")))

    def test_worker_continues_after_error_without_reusing_old_outputs(self):
        good = self.root / "good.json"
        bad = self.root / "bad.json"
        good.write_text(json.dumps(self.spec()))
        bad.write_text(json.dumps({**self.spec(), "sha256": "bad"}))
        arguments = [str(good), str(self.root / "row.json"), str(self.root / "images")]
        requests = [
            {"requestId": 1, "arguments": arguments},
            {"requestId": 2, "arguments": [str(bad), *arguments[1:]]},
            {"requestId": 3, "arguments": arguments},
        ]
        process = subprocess.run(
            [sys.executable, "-m", "build.worker", "render", "--persistent_worker"],
            input="".join(json.dumps(r) + "\n" for r in requests),
            env={
                **os.environ,
                "PYTHONPATH": os.pathsep.join(
                    str(Path(p).resolve()) for p in sys.path if p
                ),
            },
            capture_output=True,
            text=True,
            check=True,
        )
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([r["exitCode"] for r in replies], [0, 1, 0])
        self.assertEqual([r["requestId"] for r in replies], [1, 2, 3])
        self.assertTrue((self.root / "images/image.png").exists())

    def test_index_lists_each_library_score_in_configured_order(self):
        paths = []
        for library, status, score in [("b", "rendered", 0.75), ("a", "error", 0), ("c", "rendered", None)]:
            path = self.root / (library + ".json")
            path.write_text(json.dumps(dict(case="one", library=library, status=status, score=score)))
            paths.append(str(path))
        base = "docs/benchmarks/accuracy/comparisons/layout"
        write(dict(mode="index", rows=paths, page=base + "/README.md", base=base,
                   suite="layout-accuracy", title="Layout", cases=[dict(name="one", group="test")],
                   libraries=["a", "b", "c"]), self.root / "pages")
        text = (self.root / "pages" / base / "README.md").read_text()
        self.assertIn("[a IoU](libraries/a.md) | [b IoU](libraries/b.md) | [c IoU](libraries/c.md)", text)
        self.assertIn("| error · 0.00% IoU | rendered · 75.00% IoU | rendered · unscored |", text)
        self.assertIn("../cases/layout-accuracy-one.md", text)
        self.assertNotIn("See all renderers", text)

    def test_markdown_does_not_read_images(self):
        row = self.root / "row.json"
        row.write_text(
            json.dumps(
                {
                    "case": "one",
                    "library": "example",
                    "status": "error",
                    "score": 0,
                    "error": "unsupported",
                }
            )
        )
        spec = {
            "mode": "case",
            "rows": [str(row)],
            "page": "docs/cases/one.md",
            "base": "docs",
            "renders": "renders",
            "title": "one",
            "cases": [{"name": "one", "group": "test"}],
            "libraries": ["example"],
            "source": "one.zpl",
            "reference": None,
        }
        write(spec, self.root / "pages")
        text = (self.root / "pages/docs/cases/one.md").read_text()
        self.assertIn("Render failed; no image", text)
        self.assertIn("unsupported", text)


if __name__ == "__main__":
    unittest.main()

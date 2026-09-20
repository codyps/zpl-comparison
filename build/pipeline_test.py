"""Behavioral tests for independently cached actions and optional image outputs."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from benchmarks.accuracy.pixels import sha
from build.compare import comparison
from build.pages import write
from build.render import render
from build.stage import stage


class PipelineTest(unittest.TestCase):
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

"""Exercise staging and child-process dependency isolation without the full corpus."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from build.stage import stage


class ReportRunnerTests(unittest.TestCase):
    def test_assembly_merges_inputs_and_runs_checks_without_copying_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = root / "first", root / "second"
            first.mkdir()
            second.mkdir()
            (first / "report.txt").write_text("old")
            (second / "report.txt").write_text("new")
            (second / "report.txt").chmod(0o444)
            check = root / "check.py"
            check.write_text("import os\nfrom pathlib import Path\n"
                             "assert Path('docs/report.txt').read_text() == 'new'\n"
                             "Path(os.environ['HOME']).mkdir()\n"
                             "Path(os.environ['HOME'], 'cache').write_text('temporary')\n")
            output = root / "output"
            stage(dict(inputs=[[str(first), "docs"], [str(second), "docs"],
                               [str(check), "check.py"]], commands=[["check.py"]], assemble=True), output)
            self.assertEqual((output / "docs/report.txt").read_text(), "new")
            self.assertEqual((second / "report.txt").read_text(), "new")
            self.assertFalse((output / "docs/report.txt").is_symlink())
            self.assertEqual({str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()},
                             {"docs/report.txt", "check.py"})

    def test_read_only_tree_artifact_can_be_updated_without_mutating_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact"
            artifact.mkdir()
            (artifact / "README.md").write_text("earlier report")
            (artifact / "README.md").chmod(0o444)
            script = root / "update.py"
            script.write_text("from pathlib import Path; Path('docs/README.md').write_text('complete report')")
            stage({"inputs": [[str(artifact), "docs"], [str(script), "update.py"]], "commands": [["update.py"]]}, root / "output")
            self.assertEqual((root / "output/docs/README.md").read_text(), "complete report")
            self.assertEqual((artifact / "README.md").read_text(), "earlier report")

    def run_pipeline(self, source, root):
        script = root / "regenerate.py"
        script.write_text(source)
        evidence = root / "evidence.json"
        evidence.write_text('{"saved": true}\n')
        manifest = root / "inputs.json"
        manifest.write_text(
            json.dumps(
                [
                    [str(script), "benchmarks/regenerate.py"],
                    [str(evidence), "docs/evidence.json"],
                ]
            )
        )
        output = root / "reports"
        stage({"inputs": json.loads(manifest.read_text()), "commands": [["benchmarks/regenerate.py"]]}, output)
        return evidence, output

    def test_child_imports_wheels_and_only_mutates_copied_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence, output = self.run_pipeline(
                "from pathlib import Path\n"
                "from PIL import Image\n"
                "Path('docs/evidence.json').write_text('staged')\n"
                "Image.new('RGB', (2, 2)).save('docs/report.png')\n",
                Path(tmp),
            )
            self.assertEqual(evidence.read_text(), '{"saved": true}\n')
            self.assertEqual((output / "docs/evidence.json").read_text(), "staged")
            self.assertFalse((output / "docs/evidence.json").is_symlink())
            self.assertTrue((output / "docs/report.png").is_file())

    def test_failed_generator_fails_the_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(subprocess.CalledProcessError) as raised:
                self.run_pipeline("raise SystemExit(7)\n", Path(tmp))
            self.assertEqual(raised.exception.returncode, 7)


if __name__ == "__main__":
    unittest.main()

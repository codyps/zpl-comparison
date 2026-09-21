"""Exercise staging and child-process dependency isolation without the full corpus."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from build.stage import stage


class ReportRunnerTests(unittest.TestCase):
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

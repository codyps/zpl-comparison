"""Source evidence must describe the selected sources and preserve distinctions."""

import json
from pathlib import Path
import unittest


class SupportTest(unittest.TestCase):
    def test_current_source_evidence(self):
        data = json.loads(Path("reports_actions/support/docs/benchmarks/command-support.json").read_text())
        self.assertEqual(data["sources"], json.loads(Path("benchmarks/sources.lock.json").read_text()))
        commands = data["commands"]
        self.assertEqual(commands["go"]["^XZ"]["status"], "D")
        self.assertEqual(commands["go"]["^B3"]["status"], "I")
        self.assertEqual(commands["ffi"], commands["go"])
        self.assertEqual(commands["builder"]["^BC"]["status"], "E")
        self.assertEqual(commands["toolchain"]["^BQ"]["status"], "T")


if __name__ == "__main__":
    unittest.main()

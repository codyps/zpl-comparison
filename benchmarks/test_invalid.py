"""Malformed input must not earn rejection credit from a broken adapter/control."""

import importlib.util
from pathlib import Path
import os
import sys
import tempfile
import unittest

import invalid


class InvalidTests(unittest.TestCase):
    def test_fixture_generation_and_hashes(self):
        spec = importlib.util.spec_from_file_location(
            "invalid_generator", invalid.SUITE / "generate.py"
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        generated = generator.artifacts()
        for name, data in generated.items():
            self.assertEqual((invalid.SUITE / name).read_bytes(), data)
        manifest = invalid.load_cases()
        self.assertEqual(len(manifest["cases"]), 18)
        self.assertEqual(sum(len(m) for m in invalid.LANES.values()), 21)
        self.assertEqual(invalid.LANES["codyps-zpl-node"], ["render"])
        self.assertEqual(invalid.LANES["codyps-zpl-go"], ["render"])
        self.assertEqual(invalid.LANES["zpl-renderer-js"], ["render"])
        for case in manifest["cases"]:
            self.assertNotEqual(case["control"]["sha256"], case["invalid"]["sha256"])

    def test_rejection_requires_valid_control(self):
        accepted = [dict(status="accepted", ink=1)] * 2
        rejected = [dict(status="rejected")] * 2
        self.assertEqual(invalid.classify(accepted, rejected, "render"), "rejected")
        self.assertEqual(
            invalid.classify(rejected, rejected, "parse"), "control failed"
        )
        self.assertEqual(
            invalid.classify([dict(status="accepted", ink=0)] * 2, rejected, "render"),
            "control failed",
        )
        self.assertEqual(
            invalid.classify(accepted, [dict(status="accepted-empty")] * 2, "render"),
            "accepted",
        )

    def test_faults_and_instability_never_pass(self):
        accepted = [dict(status="accepted")] * 2
        for fault in invalid.FAULTS:
            self.assertEqual(
                invalid.classify(accepted, [dict(status=fault)] * 2, "parse"),
                "execution failure",
            )
        self.assertEqual(
            invalid.classify(
                accepted, [dict(status="accepted"), dict(status="rejected")], "parse"
            ),
            "unstable",
        )
        changed = [
            dict(status="accepted", ink=1, image_sha256=n) for n in ["one", "two"]
        ]
        self.assertEqual(invalid.classify(changed, accepted, "render"), "unstable")

    def test_process_protocol_and_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output.png"

            def probe(code, mode="parse", timeout=2):
                return invalid.attempt(
                    [sys.executable, "-c", code],
                    os.environ.copy(),
                    Path(tmp) / "input.zpl",
                    output,
                    mode,
                    timeout,
                )

            self.assertEqual(probe("print('rejected')")["status"], "rejected")
            self.assertEqual(probe("print('accepted')")["status"], "accepted")
            self.assertEqual(
                probe("print('accepted')", "render")["status"], "harness-error"
            )
            self.assertEqual(probe("print('noise')")["status"], "harness-error")
            self.assertEqual(probe("raise SystemExit(1)")["status"], "process-error")
            self.assertEqual(
                probe("import sys;sys.stderr.write('panicked at probe');sys.exit(101)")[
                    "status"
                ],
                "crash",
            )
            self.assertEqual(
                probe("import time;time.sleep(2)", timeout=0.05)["status"], "timeout"
            )

    def test_incomplete_matrix_and_repetitions_are_rejected(self):
        data = dict(
            cases=[dict(id="case")],
            lanes={"codyps-zpl": ["parse"]},
            repeats=2,
            results=[],
        )
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            invalid.render_report(data, Path("."))
        data["results"] = [
            dict(
                case="case",
                library="codyps-zpl",
                mode="parse",
                control=[],
                invalid=[],
                outcome="rejected",
            )
        ]
        with self.assertRaisesRegex(ValueError, "repetitions"):
            invalid.render_report(data, Path("."))


if __name__ == "__main__":
    unittest.main()

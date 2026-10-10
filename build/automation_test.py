"""The automation boundary must preserve evidence and reject stale replay."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build.baseline import campaign, export, normalize, sha
from build.probe import probe
from build.observation_inputs import identities, SOURCE


class AutomationTest(unittest.TestCase):
    def test_each_campaign_renderer_is_exported_with_its_own_image(self):
        rows = []
        for library in ["go", "zebrash", "labelary"]:
            image = self.root / (library + ".png")
            image.write_bytes(library.encode())
            rows.append(dict(case="sample-zq610", library=library, status="rendered", image=image.name,
                             render_sha256=sha(image), observed_utc="recorded"))
        rows.append(dict(case="sample-zq610", library="forge", status="error", diagnostic="unsupported"))
        output = self.root / "bundle"
        campaign(self.root, output, dict(results=rows, measured_utc="recorded"), "paired", "revision")
        for row in rows:
            key = row["case"] + "-" + row["library"]
            saved = json.loads((output / "rows/paired" / (key + ".json")).read_text())
            self.assertEqual(saved["library"], row["library"])
            image = output / "images/paired" / (key + ".png")
            self.assertEqual(image.exists(), row["status"] == "rendered")
            if image.exists():
                self.assertEqual(image.read_bytes(), row["library"].encode())

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_replay_identity_covers_execution_inputs_but_not_reports(self):
        files = {}
        for index, (name, content) in enumerate({
            "benchmarks/sources.lock.json": json.dumps({source: dict(rev="selected") for source in SOURCE.values()}),
            "benchmarks/adapters/go/main.go": "adapter",
            "benchmarks/adapters/codyps-zpl-go/main.go": "wasm2go-adapter",
            "benchmarks/adapters/zebrash/main.go": "native-zebrash",
            "benchmarks/adapters/node/renderers.mjs": "node-zebrash",
            "benchmarks/adapters/node/session.mjs": "node-session",
            "build/renderer_session.py": "renderer-pool",
            "benchmarks/adapters/zpl-renderer-js/package-lock.json": "wasm-dependencies",
            "benchmarks/adapters/zebrash-ts/package-lock.json": "ts-dependencies",
            "benchmarks/accuracy/pixels.py": "normalize",
            "build/requirements.lock.txt": "dependencies",
            "build/native.bzl": "deployment",
            "build/dotnet_runtime.py": "icu-packaging",
            "build/dotnet_deps.bzl": "nuget-graph",
            "build/dotnet_toolchain.BUILD": "dotnet-toolchain",
            "build/patches/rules_dotnet-hermetic-publish.patch": "hermetic-publish",
            "MODULE.bazel": "rules-versions",
            "build/probe.py": "probe",
            "build/compare.py": "comparison",
        }.items()):
            path = self.root / str(index)
            path.write_text(content)
            files[name] = str(path)
        original = identities(files, python_version="3.13")
        original_probe = identities(files, probe=True, python_version="3.13")
        for name, changed in [
            ("benchmarks/adapters/go/main.go", {"go", "ffi"}),
            ("benchmarks/adapters/codyps-zpl-go/main.go", {"codyps-zpl-go"}),
            ("benchmarks/adapters/zebrash/main.go", {"zebrash"}),
            ("benchmarks/adapters/node/renderers.mjs", {"zplr", "zpl-renderer-js", "zebrash-ts", "codyps-zpl-node"}),
            ("benchmarks/adapters/node/session.mjs", {"zplr", "zpl-renderer-js", "zebrash-ts", "codyps-zpl-node"}),
            ("build/renderer_session.py", set(SOURCE)),
            ("benchmarks/adapters/zpl-renderer-js/package-lock.json", {"zpl-renderer-js"}),
            ("benchmarks/adapters/zebrash-ts/package-lock.json", {"zebrash-ts"}),
            ("benchmarks/accuracy/pixels.py", set(SOURCE)),
            ("build/requirements.lock.txt", set(SOURCE)),
            ("build/native.bzl", set(SOURCE)),
            ("build/dotnet_runtime.py", {"binarykits"}),
            ("build/dotnet_deps.bzl", {"binarykits"}),
            ("build/dotnet_toolchain.BUILD", {"binarykits"}),
            ("build/patches/rules_dotnet-hermetic-publish.patch", {"binarykits"}),
            ("MODULE.bazel", set(SOURCE)),
            ("build/compare.py", set()),
            ("build/probe.py", set()),
        ]:
            path = Path(files[name])
            content = path.read_text()
            path.write_text(content + " changed")
            actual = identities(files, python_version="3.13")
            self.assertEqual({key for key in actual if actual[key] != original[key]}, changed, name)
            if name == "build/probe.py":
                self.assertNotEqual(identities(files, probe=True, python_version="3.13"), original_probe)
            path.write_text(content)
        self.assertNotEqual(identities(files, python_version="3.14"), original)

    def test_bundle_hashes_and_path_boundaries(self):
        source = self.root / "source"
        source.mkdir()
        (source / "result.json").write_text('{"status":"error"}')
        manifest = dict(schema=1, revision="recorded", files={"result.json": sha(source / "result.json")})
        (source / "bundle.json").write_text(json.dumps(manifest))
        normalize(source, self.root / "copy", "recorded")
        self.assertEqual((self.root / "copy/result.json").read_bytes(), (source / "result.json").read_bytes())
        self.assertEqual(json.loads((self.root / "copy/bundle.json").read_text())["revision"], "recorded")
        for name in ["first.tar.gz", "second.tar.gz"]:
            export(source, self.root / name, "recorded")
        self.assertEqual(sha(self.root / "first.tar.gz"), sha(self.root / "second.tar.gz"))
        with self.assertRaisesRegex(ValueError, "revision"):
            normalize(source, self.root / "wrong-revision", "different")
        (source / "result.json").write_text("changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            normalize(source, self.root / "bad", "recorded")
        manifest["files"] = {"../outside.json": "digest"}
        (source / "bundle.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            normalize(source, self.root / "escape", "recorded")

    def probe_spec(self):
        library = self.root / "adapter"
        library.mkdir()
        (library / "command.json").write_text('["adapter"]')
        (library / "identity.json").write_text("[]")
        case = dict(id="paired-case")
        sources = {}
        for name in ["control", "invalid"]:
            path = self.root / (name + ".zpl")
            path.write_text(name)
            sources[name] = str(path)
            case[name] = dict(sha256=sha(path))
        return dict(case=case, library="example", deployment=str(library), mode="parse",
                    input_identity="selected-inputs", repeats=2, timeout=10, sources=sources)

    def test_probe_repeats_both_inputs_and_replays_only_matching_evidence(self):
        spec = self.probe_spec()
        calls = []
        def attempt(command, env, source, output, mode, timeout):
            calls.append(source.name)
            return dict(status="accepted" if source.name == "control.zpl" else "rejected")
        baseline = self.root / "baseline.json"
        with patch("build.probe.attempt", side_effect=attempt):
            probe(spec, baseline)
        self.assertEqual(calls, ["control.zpl", "control.zpl", "invalid.zpl", "invalid.zpl"])
        self.assertEqual(json.loads(baseline.read_text())["outcome"], "rejected")
        spec["baseline"] = str(baseline)
        with patch("build.probe.attempt", side_effect=AssertionError("Replay must not execute")):
            probe(spec, self.root / "replay.json")
            self.assertEqual(json.loads((self.root / "replay.json").read_text())["outcome"], "rejected")
            spec["input_identity"] = "changed-adapter"
            probe(spec, self.root / "stale.json")
            self.assertEqual(json.loads((self.root / "stale.json").read_text())["outcome"], "not measured")

    def test_probe_protocol_failure_fails_the_action(self):
        spec = self.probe_spec()
        with patch("build.probe.attempt", return_value=dict(status="harness-error")):
            with self.assertRaisesRegex(ValueError, "harness/protocol"):
                probe(spec, self.root / "failed.json")
        self.assertEqual(json.loads((self.root / "failed.json").read_text())["outcome"], "execution failure")


if __name__ == "__main__":
    unittest.main()

"""Exercise real child-process timing collection without downloading renderers."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from build.performance import collect
from build.native_build import source_size


class PerformanceTest(unittest.TestCase):
    def test_source_size_excludes_tests_and_counts_selected_implementation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "benchmarks/_work/go-zpl"
            source.mkdir(parents=True)
            (source / "render.go").write_text("package zpl\n// renderer\n")
            (source / "render_test.go").write_text("test")
            size = source_size(root, "go")
            self.assertEqual(size["files"], 1)
            self.assertEqual(size["lines"], 2)
            self.assertEqual(size["bytes"], 24)
            self.assertEqual(size["source_manifest"][0]["name"], "benchmarks/_work/go-zpl/render.go")
            with self.assertRaisesRegex(ValueError, "Missing implementation"):
                source_size(root, "zplr")

    def test_collect_executes_children_and_retains_raw_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "library_go"
            library.mkdir()
            adapter = library / "adapter.py"
            adapter.write_text('''import json, sys, time
from pathlib import Path
mode, fixture, count, output = sys.argv[1:]
if mode == "png":
    raise SystemExit(2)
count = int(count)
start = time.monotonic_ns()
checksum = sum(len(Path(fixture).read_bytes()) for _ in range(count))
ns = time.monotonic_ns() - start
Path(output).write_text(str(checksum))
print(json.dumps(dict(ns=ns, iterations=count, checksum=checksum)))
''')
            (library / "command.json").write_text(json.dumps([sys.executable, "adapter.py"]))
            (library / "identity.json").write_text('[]')
            (library / "size.json").write_text('{"bytes": 42, "artifact_bytes": 99}')
            fixtures = root / "fixtures"
            fixtures.mkdir()
            (fixtures / "text.zpl").write_text('^XA^XZ')
            with patch('build.performance.LIBRARIES', ('go',)):
                collect(root, fixtures, root / "first", samples=2, seconds=.001)
                (fixtures / "text.zpl").write_text('^XA^FO10,10^FDfresh^FS^XZ')
                collect(root, fixtures, root / "second", samples=2, seconds=.001)
            first, second = [json.loads((root / name / "results.json").read_text()) for name in ('first', 'second')]
            rows = [next(r for r in data['results'] if r['mode'] == 'parse') for data in (first, second)]
            self.assertNotEqual(rows[0]['input_sha256'], rows[1]['input_sha256'])
            for data, row in zip((first, second), rows):
                self.assertEqual(data['sizes']['go']['artifact_bytes'], 99)
                self.assertEqual(row['status'], 'ok')
                self.assertEqual(len(row['samples']), 2)
                self.assertGreater(row['median_ns'], 0)
                self.assertGreater(row['peak_rss_bytes'], 0)
                self.assertEqual(next(r for r in data['results'] if r['mode'] == 'png')['status'], 'failed')

    def test_all_failed_adapter_retains_diagnostics_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "library_go"
            library.mkdir()
            (library / "command.json").write_text(json.dumps([sys.executable, "-c", "raise SystemExit(2)"]))
            (library / "identity.json").write_text('[]')
            (library / "size.json").write_text('{"bytes": 42, "artifact_bytes": 99}')
            (root / "text.zpl").write_text('^XA^XZ')
            with patch('build.performance.LIBRARIES', ('go',)):
                with self.assertRaisesRegex(RuntimeError, "No successful measurements"):
                    collect(root, root, root / 'output', samples=1)
            data = json.loads((root / 'output/results.json').read_text())
            self.assertTrue(all(r['status'] == 'failed' for r in data['results']))

    def test_missing_deployment_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                collect(root, root, root / 'output')


if __name__ == '__main__':
    unittest.main()

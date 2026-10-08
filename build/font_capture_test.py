"""Physical font capture provenance and comparison regression tests (offline)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks.fonts import capture
from build.compare import comparison


class FontCaptureTest(unittest.TestCase):
    def test_extension_archives_evidence_without_promoting_uncaptured_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'capture'
            path = 'inputs/manifest.json'
            old = b'{"cases": ["old"]}'
            current = b'{"cases": ["old", "new"]}'
            (root / path).parent.mkdir(parents=True)
            (root / path).write_bytes(current)
            snapshot = out / 'source-manifests' / path
            snapshot.parent.mkdir(parents=True)
            snapshot.write_bytes(old)
            record = dict(status='complete', finished_utc='before', cases={'old.png': {'session': 1}},
                          source_manifests={path: capture.sha(old)}, sessions=[{'status': 'complete'}])
            capture.save(out / 'capture.json', record)
            previous = (out / 'capture.json').read_bytes()
            with patch.object(capture, 'ROOT', root), \
                 patch.object(capture, 'verify', return_value=record) as verify, \
                 patch.object(capture, 'inventory', return_value=({path: {}}, [{'reference': n} for n in ['old.png', 'new.png']])):
                capture.extend_capture(out, root / 'bundle')
            verify.assert_called_once_with(out, root / 'bundle', allow_new=True)
            saved = json.loads((out / 'capture.json').read_text())
            self.assertEqual(saved['status'], 'incomplete')
            self.assertEqual(set(saved['cases']), {'old.png'})
            self.assertEqual(saved['sessions'], [{'status': 'complete'}])
            self.assertEqual(saved['source_manifests'][path], capture.sha(current))
            history = out / saved['extensions'][0]['previous_capture']
            self.assertEqual(history.read_bytes(), previous)
            self.assertEqual((history.parent / 'source-manifests' / path).read_bytes(), old)
            self.assertEqual(snapshot.read_bytes(), current)
            self.assertEqual(json.loads((out / 'catalog.json').read_text())['_capture_status'], 'incomplete')

    def test_evidence(self):
        record = capture.verify(Path('references/font-controlled'), Path('comparison_fonts'))
        self.assertEqual({s['printer'] for s in record['sessions']}, {'zd621', 'zq610'})
        catalog = json.loads(Path('references/font-controlled/catalog.json').read_text())
        self.assertEqual(catalog.pop("_capture_status"), "complete")
        for path, manifest in catalog.items():
            self.assertEqual(manifest, json.loads((Path('references/font-controlled/overlay') / path).read_text()))
            self.assertEqual(manifest['font_capture']['bundle_sha256'], record['font_control']['bundle_sha256'])
            self.assertEqual(manifest['font_capture']['capture_sha256'], capture.sha(Path('references/font-controlled/capture.json').read_bytes()))

    def test_snapshot_rejects_changes_to_existing_captured_inputs(self):
        root = Path('references/font-controlled')
        record = json.loads((root / 'capture.json').read_text())
        originals, cases = capture.inventory()
        inventory = capture.inventory
        for changed in ('remove', 'modify'):
            current = [dict(c) for c in cases]
            if changed == 'remove':
                current.pop(0)
            else:
                current[0]['width'] += 1
            def altered(manifests=None):
                return (originals, current) if manifests is None else inventory(manifests)
            with self.subTest(changed=changed), patch.object(capture, 'inventory', side_effect=altered):
                with self.assertRaisesRegex(ValueError, 'Captured input changed or removed'):
                    capture.captured_inventory(root, record)

    def test_new_inputs_require_fresh_controlled_captures(self):
        originals, cases = capture.inventory()
        inventory = capture.inventory
        extra = {**cases[0], 'reference': 'new-uncaptured.png'}
        def extended(manifests=None):
            return (originals, cases + [extra]) if manifests is None else inventory(manifests)
        with patch.object(capture, 'inventory', side_effect=extended):
            with self.assertRaisesRegex(ValueError, 'New inputs require --extend'):
                capture.verify(Path('references/font-controlled'), Path('comparison_fonts'))

    def test_changed_source_snapshot_is_rejected(self):
        root = Path('references/font-controlled')
        record = json.loads((root / 'capture.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            path = out / 'source-manifests' / capture.STANDARD[1]
            path.parent.mkdir(parents=True)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Printer source manifests changed'):
                capture.captured_inventory(out, record)

    def test_submission_preserves_fixture_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = b'^XA^PW128^LL91^CFD,18^FO1,2^FD0123^FS^XZ'
            (root / 'case.zpl').write_bytes(source)
            case = dict(source='case.zpl', source_sha256=capture.sha(source), width=832, height=300, ram_resources=False)
            with patch.object(capture, 'ROOT', root):
                setup, submitted = capture.submission(case, b'^CWD,R:FCD.FNT')
                self.assertEqual(setup, b'')
                self.assertTrue(submitted.endswith(source[3:]))
                self.assertLess(submitted.index(b'^CWD'), submitted.index(b'^PW128'))
                (root / 'case.zpl').write_bytes(source + b'changed')
                with self.assertRaisesRegex(ValueError, 'Changed'):
                    capture.submission(case, b'')

    def test_mismatched_printer_font_bundle_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = root / 'row.json'
            row.write_text(json.dumps(dict(status='rendered', font_control={'bundle_sha256': 'renderer-fonts'})))
            with self.assertRaisesRegex(ValueError, 'font bundles differ'):
                comparison(dict(row=str(row), reference='unused.png', reference_font_control={'bundle_sha256': 'other-fonts'}), root / 'out.json', root / 'images')

    def test_incomplete_capture_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                capture.export(Path(tmp), {}, {'status': 'incomplete'}, b'')

    def test_timeout_retains_source_without_queuing_cleanup(self):
        from types import SimpleNamespace
        from PIL import Image
        import io
        from unittest.mock import MagicMock
        def png(value):
            output = io.BytesIO()
            Image.new('L', (2, 2), value).save(output, format='PNG')
            return output.getvalue(), Image.open(io.BytesIO(output.getvalue()))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = b'^XA^FDsample^FS^XZ'
            (root / 'case.zpl').write_bytes(data)
            case = dict(source='case.zpl', reference='case.png', source_sha256=capture.sha(data),
                        width=64, height=64, printer='zd621', ram_resources=False)
            printer = MagicMock()
            printer.fetch.side_effect = [
                b'ZTC ZD621-203dpi ZPL<H2>TESTSERIAL</H2>', b'V93.21.33Z FIRMWARE',
                b'', b'R:FC0.TTF',
            ]
            printer.preview.side_effect = [png(255), png(255), png(0), png(255), TimeoutError('preview stalled')]
            with patch.object(capture, 'ROOT', root), patch.object(capture, 'HOSTS', {'zd621': 'http://printer/'}), \
                 patch.object(capture, 'inventory', return_value=({}, [case])), \
                 patch.object(capture, 'fonts', return_value=({}, b'upload', b'^CW0,R:FC0.TTF', ['R:FC0.TTF'])), \
                 patch.object(capture, 'Printer', return_value=printer), patch.object(capture.time, 'sleep'):
                with self.assertRaisesRegex(TimeoutError, 'preview stalled'):
                    capture.capture(SimpleNamespace(output=root / 'output', bundle=root, interval=0))
            self.assertEqual(printer.preview.call_count, 5)
            record = json.loads((root / 'output/capture.json').read_text())
            self.assertEqual(record['inflight'], 'case.png')
            self.assertEqual(record['sessions'][0]['status'], 'interrupted')
            self.assertEqual(record['inflight_sha256'], capture.sha((root / 'output/submitted/case.zpl').read_bytes()))
            self.assertEqual(record['cases'], {})

    def test_overlay_export_retains_source_identity(self):
        root = Path('references/font-controlled')
        record = json.loads((root / 'capture.json').read_text())
        originals, _ = capture.inventory()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            # Export into a distinct tree; paired metadata measures the captured pixels.
            import shutil
            shutil.copytree(root / 'overlay', out / 'overlay')
            capture.export(out, originals, record, capture.fonts(Path('comparison_fonts'))[2])
            exported = json.loads((out / 'catalog.json').read_text())
            for path in capture.STANDARD:
                old = {r['name']: r for r in originals[path]['cases']}
                for row in exported[path]['cases']:
                    self.assertEqual(row['zpl_sha256'], old[row['name']]['zpl_sha256'])
                    key = str(Path(path).parent / (row['name'] + '.png'))
                    self.assertEqual(row['png_sha256'], record['cases'][key]['png_sha256'])
                self.assertEqual({r['name'] for r in exported[path]['cases']}, set(old))
                self.assertNotIn('refresh_batches', exported[path])
            self.assertEqual(exported, json.loads((root / 'catalog.json').read_text()))


if __name__ == '__main__':
    unittest.main()

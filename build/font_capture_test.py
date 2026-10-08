"""Physical font capture provenance and comparison regression tests (offline)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks.fonts import capture
from build.compare import comparison


class FontCaptureTest(unittest.TestCase):
    def test_evidence(self):
        record = capture.verify(Path('references/font-controlled'), Path('comparison_fonts'))
        self.assertEqual({s['printer'] for s in record['sessions']}, {'zd621', 'zq610'})
        catalog = json.loads(Path('references/font-controlled/catalog.json').read_text())
        self.assertEqual(catalog.pop("_capture_status"), "complete")
        for path, manifest in catalog.items():
            self.assertEqual(manifest, json.loads((Path('references/font-controlled/overlay') / path).read_text()))
            self.assertEqual(manifest['font_capture']['bundle_sha256'], record['font_control']['bundle_sha256'])
            self.assertEqual(manifest['font_capture']['capture_sha256'], capture.sha(Path('references/font-controlled/capture.json').read_bytes()))

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
                self.assertNotIn('refresh_batches', exported[path])
            self.assertEqual(exported, json.loads((root / 'catalog.json').read_text()))


if __name__ == '__main__':
    unittest.main()

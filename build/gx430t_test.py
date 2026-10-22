"""Check imported hardware evidence and reject corrupted or relabeled captures."""
from contextlib import chdir
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from benchmarks.gx430t import ROOT, verify


class GX430tEvidenceTest(unittest.TestCase):
    def test_retained_native_previews_and_control_receipts(self):
        manifest = verify()
        self.assertEqual(len(manifest['cases']), 34)
        self.assertEqual({(c['width'], c['height']) for c in manifest['cases']}, {(832, 2558)})
        self.assertEqual({c['group'] for c in manifest['cases']}, {'text', 'layout', 'shapes', 'graphics', 'barcodes'})
        self.assertEqual(manifest['device']['firmware'], 'V56.17.17Z')

    def test_every_case_has_a_verified_12dpmm_labelary_response(self):
        from benchmarks.gx430t_labelary import validate
        captures = validate()
        self.assertEqual((captures['dpmm'], captures['dpi'], captures['canvas_dpi']), (12, 300, 304))
        self.assertEqual(len(captures['cases']), 34)
        self.assertEqual({tuple(c['dimensions']) for c in captures['cases']}, {(832, 2558)})
        self.assertTrue(all(c['status'] == 'rendered' for c in captures['cases']))

    def test_changed_image_and_mislabeled_density_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / ROOT
            shutil.copytree(ROOT, target)
            with chdir(temporary):
                image = ROOT / 'argument-font-A.png'
                original = image.read_bytes()
                image.write_bytes(b'not a printer image')
                with self.assertRaisesRegex(ValueError, 'Changed GX430t evidence'):
                    verify()
                image.write_bytes(original)
                path = ROOT / 'manifest.json'
                manifest = json.loads(path.read_text())
                manifest['device']['dpi'] = 203
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'identity changed'):
                    verify()


if __name__ == '__main__':
    unittest.main()

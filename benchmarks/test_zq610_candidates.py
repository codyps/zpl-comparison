"""The ZQ610 page generator must accept the complete configured renderer matrix."""
from contextlib import chdir
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from accuracy.run import LIBRARIES
import zq610_candidate_pages as pages


class CandidatePagesTest(unittest.TestCase):
    def test_complete_matrix_publishes_neodynamic_and_rejects_missing_or_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as temporary, chdir(temporary):
            root = Path(temporary)
            capture = root / 'references/zq610-candidates'
            capture.mkdir(parents=True)
            source, reference = capture / 'sample.zpl', capture / 'sample.png'
            source.write_bytes(b'^XA^FO10,10^GB20,20,2^FS^XZ')
            Image.new('L', (32, 32), 255).save(reference)
            manifest = dict(cases=[dict(name='sample', source=str(source.relative_to(root)),
                                       reference=str(reference.relative_to(root)),
                                       sha256=pages.sha(source), png_sha256=pages.sha(reference))])
            (capture / 'manifest.json').write_text(json.dumps(manifest))
            (root / 'benchmarks').mkdir()
            (root / 'benchmarks/sources.lock.json').write_text('{}')
            rows = root / '_candidate_rows'
            rows.mkdir()
            for library in LIBRARIES:
                (rows / (library + '.json')).write_text(json.dumps(dict(
                    case='sample', library=library, status='not_captured', score=None)))
            pages.generate()
            result = json.loads((pages.BASE / 'results.json').read_text())
            self.assertEqual(set(result['libraries']), set(LIBRARIES))
            self.assertIn('neodynamic', result['libraries'])
            self.assertEqual(len(result['results']), len(LIBRARIES))
            self.assertIn('<h2>neodynamic</h2>', (pages.BASE / 'sample/index.html').read_text())
            row = rows / 'neodynamic.json'
            saved = row.read_text()
            row.unlink()
            with self.assertRaisesRegex(ValueError, 'candidate matrix'):
                pages.generate()
            row.write_text(saved)
            (rows / 'duplicate.json').write_text(saved)
            with self.assertRaisesRegex(ValueError, 'candidate matrix'):
                pages.generate()


if __name__ == '__main__':
    unittest.main()

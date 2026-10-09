"""Exercise the Git-built Node/Wasm package through the comparison protocol."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from PIL import Image


class NodeAdapterTest(unittest.TestCase):
    def setUp(self):
        deployment = Path('library_codyps-zpl-node').resolve()
        self.command = [str(deployment / arg) if (deployment / arg).exists() else arg
                        for arg in json.loads((deployment / 'command.json').read_text())]
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'input.zpl'
        self.output = self.root / 'output.png'

    def invoke(self, mode, source, profile='zd621-203dpi'):
        self.source.write_bytes(source)
        self.output.unlink(missing_ok=True)
        return subprocess.run(
            self.command + [mode, str(self.source), '2', str(self.output), '192', '120'],
            env={**os.environ, 'ZPL_RENDER_PROFILE': profile, 'ZPL_BENCH_MEMORY': '1'},
            cwd=self.root, capture_output=True, text=True, timeout=30, check=True)

    def test_render_timing_and_binary_graphics(self):
        suffix = b'^FS^XZ'
        pixels = []
        for graphic in [b'^GFB,4,4,1,\xff\x81\x81\xff', b'^GFA,4,4,1,FF8181FF']:
            result = self.invoke('png', b'^XA^FO10,60' + graphic + suffix)
            timing = json.loads(result.stdout)
            self.assertEqual(timing['iterations'], 2)
            self.assertGreater(timing['ns'], 0)
            self.assertGreater(timing['checksum'], 0)
            with Image.open(self.output) as image:
                self.assertEqual(image.size, (192, 120))
                pixels.append(image.convert('L').tobytes())
                self.assertEqual(sum(v < 128 for v in image.convert('L').crop((10, 60, 18, 64)).getdata()), 20)
        self.assertEqual(*pixels)

    def test_probes_reject_missing_and_multiple_labels(self):
        for source in [b'', b'^XA^FO10,10^GB20,20,2^FS^XZ' * 2]:
            result = self.invoke('probe-render', source)
            self.assertEqual(result.stdout.strip(), 'rejected')
            self.assertFalse(self.output.exists())
        result = self.invoke('probe-render', b'^XA^FO10,10^GB20,20,2^FS^XZ')
        self.assertEqual(result.stdout.strip(), 'accepted', result.stderr)
        self.assertTrue(self.output.exists())

    def test_input_limit_is_reported_as_rejection(self):
        result = self.invoke('probe-render', b' ' * (1024 * 1024 + 1))
        self.assertEqual(result.stdout.strip(), 'rejected')
        self.assertIn('1 MiB', result.stderr)
        self.assertFalse(self.output.exists())

    def test_public_profiles_and_render_only_adapter(self):
        source = b'^XA^FO10,10^GB20,20,2^FS^XZ'
        for profile in ['zd621-203dpi', 'zd621-preview-203dpi', 'zq610-plus-203dpi']:
            self.invoke('accuracy', source, profile)
            with Image.open(self.output) as image:
                self.assertEqual(image.size, (192, 120))
        result = self.invoke('probe-parse', source)
        self.assertEqual(result.stdout.strip(), 'rejected')
        self.assertIn('adapter does not expose parsing', result.stderr)


if __name__ == '__main__':
    unittest.main()

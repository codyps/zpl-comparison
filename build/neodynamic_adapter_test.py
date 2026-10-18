"""Exercise the real SDK, including binary input and virtual-printer isolation."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from PIL import Image
from build import renderer_session as sessions
from build.native_build import source_size


class NeodynamicAdapterTest(unittest.TestCase):
    def setUp(self):
        self.deployment = Path('library_neodynamic').resolve()
        self.command = [str(self.deployment / value) if (self.deployment / value).exists() else value
                        for value in json.loads((self.deployment / 'command.json').read_text())]
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = {**os.environ, 'DOTNET_ROOT': str(self.deployment / 'runtime'),
                    'DOTNET_CLI_HOME': str(self.root), 'HOME': str(self.root), 'TMPDIR': str(self.root),
                    'LD_LIBRARY_PATH': str(self.deployment) + os.pathsep + os.environ.get('LD_LIBRARY_PATH', ''),
                    'ZPL_FONT_DIR': '', 'ZPL_RENDER_PROFILE': 'zd621-203dpi', 'ZPL_BENCH_MEMORY': '1'}

    def invoke(self, source, mode='accuracy', width=192, height=120):
        path, image = self.root / 'input.zpl', self.root / 'output.png'
        path.write_bytes(source)
        image.unlink(missing_ok=True)
        args = [mode, str(path), '2', str(image), str(width), str(height)]
        result = subprocess.run(self.command + args, cwd=self.root, env=self.env,
                                capture_output=True, text=True, timeout=30)
        return result, args, image

    @staticmethod
    def document_ink(path):
        # Trial watermark hues vary per render. Check black document pixels only;
        # the adapter and reports always retain the complete unmodified image.
        with Image.open(path) as image:
            rgb = image.convert('RGB')
            return (image.size, [pixel == (0, 0, 0) for pixel in rgb.get_flattened_data()])

    def test_canvas_and_png_timing_protocol(self):
        source = b'^XA^FO10,50^GB20,20,2^FS^XZ'
        result, _, image = self.invoke(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(image) as png:
            self.assertEqual(png.size, (192, 120))
        result, _, image = self.invoke(source, mode='png')
        self.assertEqual(result.returncode, 0, result.stderr)
        timing = json.loads(result.stdout)
        self.assertEqual(timing['iterations'], 2)
        self.assertGreater(timing['ns'], 0)
        self.assertGreater(timing['checksum'], 0)
        result, _, _ = self.invoke(source, mode='parse')
        self.assertNotEqual(result.returncode, 0)

    def test_binary_graphics_match_ascii_hex_without_text_decoding(self):
        prefix, suffix = b'^XA^FO10,60', b'^FS^XZ'
        result, _, image = self.invoke(prefix + b'^GFB,4,4,1,\xff\x81\x81\xff' + suffix)
        self.assertEqual(result.returncode, 0, result.stderr)
        binary = self.document_ink(image)
        result, _, image = self.invoke(prefix + b'^GFA,4,4,1,FF8181FF' + suffix)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(binary, self.document_ink(image))
        with Image.open(image) as png:
            self.assertEqual(sum(pixel == (0, 0, 0) for pixel in png.convert('RGB').crop((10, 60, 18, 64)).get_flattened_data()), 20)

    def test_probe_empty_and_multiple_label_contracts(self):
        result, _, image = self.invoke(b'', mode='probe-render')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'accepted-empty')
        self.assertFalse(image.exists())
        result, _, _ = self.invoke(b'^XA^FO10,10^GB20,20,2^FS^XZ', mode='probe-render')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'accepted')
        result, _, image = self.invoke(b'^XA^XZ^XA^XZ')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(image.exists())

    def test_session_does_not_retain_downloads_or_printer_state(self):
        self.addCleanup(sessions.close_all)
        cases = [b'^XA^FO10,50^GB30,20,3^FS^XZ',
                 b'~DGR:LEAK.GRF,4,1,FF8181FF^XA^LH30,20^POI^FO0,0^XGR:LEAK.GRF,1,1^FS^XZ',
                 b'^XA^FO0,0^XGR:LEAK.GRF,1,1^FS^XZ',
                 b'^XA^FO10,50^GB30,20,3^FS^XZ']
        for source in cases:
            fresh, args, image = self.invoke(source)
            expected = self.document_ink(image) if fresh.returncode == 0 else None
            image.unlink(missing_ok=True)
            reused = sessions.run(self.command, args, cwd=str(self.root), env=self.env,
                                  timeout=30, identity='neodynamic')
            self.assertEqual(reused.returncode, fresh.returncode, reused.stderr)
            if expected is not None:
                self.assertEqual(self.document_ink(image), expected)
        self.assertTrue(any(session.count > 1 for session in sessions._sessions.values()))

    def test_proprietary_source_is_unavailable(self):
        size = source_size(self.root, 'neodynamic')
        self.assertIn('unavailable', size['source_status'])
        self.assertNotIn('bytes', size)


if __name__ == '__main__':
    unittest.main()

"""Compare reused adapters with fresh processes across stateful request sequences."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from build import renderer_session as sessions
from build.font_profile import configure

LIBRARIES = ['zplr', 'zpl-renderer-js', 'zebrash-ts', 'codyps-zpl-node', 'binarykits']
BASIC = b'^XA^FO10,10^A0N,20,20^FDCafe^FS^FO10,45^GB30,20,3^FS^XZ'


class RendererReuseTest(unittest.TestCase):
    def test_fresh_and_reused_outputs_match_without_state_leaks(self):
        self.addCleanup(sessions.close_all)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in LIBRARIES:
                library = Path('library_' + name).resolve()
                command = [str(library / a) if (library / a).exists() else a
                           for a in json.loads((library / 'command.json').read_text())]
                metadata, preamble = configure('comparison_fonts', name)
                supplied = str(Path('comparison_fonts').resolve()) if 'callback' in metadata['mode'] else ''
                # A/B/A: dimensions, origins, orientation, downloaded graphics,
                # formats, prefixes, Unicode/binary inputs, fonts and profiles.
                cases = [
                    (BASIC, 192, 120, '', 'zd621-203dpi'),
                    (b'~DGR:LEAK.GRF,4,1,FF8181FF^XA^LH40,20^POI^FO0,0^XGR:LEAK.GRF,1,1^FS^XZ', 224, 160, '', 'zd621-203dpi'),
                    (b'^XA^FO0,0^XGR:LEAK.GRF,1,1^FS^XZ', 192, 120, '', 'zd621-203dpi'),
                    (b'^XA^DFR:LEAK.ZPL^FS^FO10,10^GB60,40,4^FS^XZ', 192, 120, '', 'zd621-203dpi'),
                    (b'^XA^XFR:LEAK.ZPL^FS^XZ', 192, 120, '', 'zd621-203dpi'),
                    (b'^XA^CC!!FO10,10!GB20,20,2!FS!XZ', 192, 120, '', 'zd621-203dpi'),
                    (BASIC, 192, 120, '', 'zq610-plus-203dpi'),
                    (preamble + BASIC, 192, 120, supplied, 'zd621-203dpi'),
                    (BASIC, 192, 120, '', 'zd621-203dpi'),
                    ('^XA^CI28^FO10,10^A0N,20,20^FDCafé^FS^XZ'.encode(), 192, 120, '', 'zd621-203dpi'),
                    (b'^XA^FO10,10^GFB,4,4,1,\xff\x81\x81\xff^FS^XZ', 192, 120, '', 'zd621-203dpi'),
                    (b'^XA^FD\xff^FS^XZ', 192, 120, '', 'zd621-203dpi'),
                    (b'', 192, 120, '', 'zd621-203dpi'),
                    (BASIC, 192, 120, '', 'zd621-203dpi'),
                ]
                reused_multiple = False
                for index, (source, width, height, fonts, profile) in enumerate(cases):
                    with self.subTest(library=name, case=index):
                        input_path = root / 'input.zpl'
                        input_path.write_bytes(source)
                        output = root / 'output.png'
                        env = {**os.environ, 'HOME': tmp, 'TMPDIR': tmp, 'DOTNET_CLI_HOME': tmp,
                               'DOTNET_ROOT': str(library / 'runtime'), 'ZPL_FONT_DIR': fonts,
                               'ZPL_RENDER_PROFILE': profile,
                               'LD_LIBRARY_PATH': str(library) + os.pathsep + os.environ.get('LD_LIBRARY_PATH', '')}
                        arguments = ['accuracy', str(input_path), '1', str(output), str(width), str(height)]
                        fresh = subprocess.run(command + arguments, cwd=tmp, env=env, capture_output=True, timeout=30)
                        expected = output.read_bytes() if fresh.returncode == 0 else None
                        output.unlink(missing_ok=True)
                        reused = sessions.run(command, arguments, cwd=tmp, env=env, timeout=30, identity=name)
                        reused_multiple |= any(s.count > 1 for k, s in sessions._sessions.items() if k[1] == name)
                        self.assertEqual(reused.returncode, fresh.returncode, reused.stderr)
                        if expected is not None:
                            self.assertEqual(output.read_bytes(), expected)
                        output.unlink(missing_ok=True)
                # Successful requests really used a process multiple times.
                self.assertTrue(reused_multiple)
                sessions.close_all()


if __name__ == '__main__':
    unittest.main()

"""Verify the relocated Linux renderer owns its ICU runtime dependency."""
import json
import os
import resource
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == 'linux', 'Linux app-local ICU packaging')
class DotnetRuntimeTest(unittest.TestCase):
    def test_relocated_runtime_uses_packaged_icu_and_requires_it(self):
        # The missing-ICU assertion intentionally aborts the child runtime.
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        original = Path('library_binarykits').resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deployment = root / 'relocated'
            # Link immutable payloads to avoid copying the entire framework;
            # removing a link below leaves the Bazel output intact.
            shutil.copytree(original, deployment, copy_function=os.symlink)
            config = json.loads((deployment / 'Comparison.runtimeconfig.json').read_text())
            version = config['runtimeOptions']['configProperties']['System.Globalization.AppLocalIcu']
            framework, = (deployment / 'runtime/shared/Microsoft.NETCore.App').iterdir()
            libraries = [framework / f'libicu{name}.so.{version}' for name in ('data', 'uc', 'i18n')]
            self.assertTrue(all(path.is_file() for path in libraries))
            self.assertTrue((framework / 'ICU-LICENSE.txt').is_file())
            identities = {entry['name'] for entry in json.loads((deployment / 'identity.json').read_text())}
            for path in libraries:
                self.assertIn(str(path.relative_to(deployment)), identities)
            source = root / 'input.zpl'
            source.write_text('^XA^FO10,10^A0N,24,16^FDHello 123^FS^XZ')
            output = root / 'output.png'
            # Copy the muxer instead of linking it: its resolved location
            # determines which shared framework directory .NET searches.
            muxer = deployment / 'runtime/dotnet'
            muxer.unlink()
            shutil.copy2(original / 'runtime/dotnet', muxer)
            command = [str(muxer), str(deployment / 'Comparison.dll'),
                       'accuracy', str(source), '1', str(output), '192', '120']
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(('DOTNET_', 'COMPlus_'))
                   and key not in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'DYLD_LIBRARY_PATH')}
            env.update(HOME=tmp, TMPDIR=tmp, DOTNET_CLI_HOME=tmp,
                       DOTNET_ROOT=str(deployment / 'runtime'))
            result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            self.assertTrue(output.read_bytes().startswith(b'\x89PNG'))
            output.unlink()
            for path in libraries:
                path.unlink()
            result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Failed to load app-local ICU', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()

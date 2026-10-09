"""Install the checksum-verified Linux ICU package into the pinned .NET SDK."""
import json
from pathlib import Path
import shutil
import sys


def install(sdk, package, rid, version):
    native = package / 'runtimes' / rid / 'native'
    libraries = [native / f'libicu{name}.so.{version}' for name in ('data', 'uc', 'i18n')]
    for library in libraries:
        if not library.is_file():
            raise ValueError('Missing pinned ICU library: ' + str(library))
    frameworks = list((sdk / 'shared/Microsoft.NETCore.App').iterdir())
    if not frameworks:
        raise ValueError('Missing .NET shared framework')
    for framework in frameworks:
        for library in libraries:
            shutil.copyfile(library, framework / library.name)
        shutil.copyfile(package / 'LICENSE', framework / 'ICU-LICENSE.txt')
    (sdk / 'icu-version.txt').write_text(version + '\n')
    # NativeLibrary probing includes the shared framework directory. Configure
    # SDK entry points too: restore/publish need ICU before the app is built.
    for path in (sdk / 'sdk').rglob('*.runtimeconfig.json'):
        config = json.loads(path.read_text())
        properties = config.setdefault('runtimeOptions', {}).setdefault('configProperties', {})
        properties['System.Globalization.AppLocalIcu'] = version
        path.write_text(json.dumps(config, indent=2) + '\n')


if __name__ == '__main__':
    install(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4])

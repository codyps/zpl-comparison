"""Font-controlled rendering policy; never rewrite fixture fields or geometry."""
import hashlib
import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

CALLBACK = {'binarykits', 'forge', 'zplr'}
DOWNLOAD = {'zebrash', 'zebrash-ts', 'zpl-renderer-js'}
FIXED = {
    'codyps-zpl-node': 'The shared font-download bundle exceeds the Node/Wasm 1 MiB input limit; no public custom font provider or limit override. Resident Wasm fonts retained.',
    'labelize': 'Fixed embedded faces; Renderer exposes no font loader.',
    'go': 'Fixed internal font manager; no public replacement API.',
    'ffi': 'Fixed go-zpl font manager behind the FFI API.',
    'labelary': 'Fixed service fonts; replay of the original captured input.',
}


def configure(directory, library):
    root = Path(directory).resolve()
    manifest_bytes = (root / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    # Persistent workers see immutable Bazel inputs during a build, but can be
    # reused after inputs change. Include file identity and change timestamps so
    # edits (even with a restored mtime) force fresh hash verification.
    signatures = []
    for name in sorted(manifest['sha256']):
        stat = (root / name).stat()
        signatures.append((name, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))
    metadata, preamble = _configure(root, library, manifest_bytes, tuple(signatures))
    return deepcopy(metadata), preamble


@lru_cache(maxsize=32)
def _configure(root, library, manifest_bytes, signatures):
    manifest = json.loads(manifest_bytes)
    for name, digest in manifest['sha256'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Font bundle hash mismatch: ' + name)
    if library == 'codyps-zpl':
        mode, note = 'supplied-bitmap-and-callback', 'Recovered native bitmap downloads via ~DB/^CW; Heros font 0 and named Swiss via Fonts/render_with_fonts with native hinting and dots-per-em sizing. GS retains its resident face; captions follow library font selection.'
    elif library == 'zplr':
        mode, note = 'supplied-bitmap-and-callback', 'Recovered native bitmap downloads via ~DB/^CW; shared TrueType font 0 via the public font API and ^CW. GS and built-in captions may retain fixed fonts.'
    elif library == 'forge':
        mode, note = 'supplied-callback', 'Recovered outlines for A–H and P–V, Heros for 0 through FontManager; GS and named fonts retain built-ins.'
    elif library in CALLBACK:
        mode, note = 'supplied-callback', 'Recovered bitmap outlines and shared TrueType substitutes through the public font API.'
    elif library in DOWNLOAD:
        mode, note = 'supplied-download', 'Shared TrueType fonts via ~DU/^CW preamble. Downloaded-font scaling applies; GS and internally generated barcode captions can retain built-in fonts.'
    elif library in FIXED:
        mode, note = 'fixed', FIXED[library]
    else:
        raise ValueError('Unknown font policy: ' + library)
    metadata = dict(profile='controlled-v1', mode=mode, note=note,
                    bundle_sha256=hashlib.sha256(manifest_bytes).hexdigest(), fonts=manifest['fonts'])
    preamble = bytearray()
    if library in {'zplr', 'codyps-zpl'}:
        preamble.extend((root / 'bitmap-download.zpl').read_bytes())
    if library in DOWNLOAD:
        for fid, filename in sorted(manifest['fonts'].items()):
            if fid == 'GS':
                continue  # ^CW only accepts a one-character alias.
            data = (root / filename).read_bytes()
            name = 'R:TT0003M_.TTF' if fid == 'TT0003M_' else 'R:FC' + fid + '.TTF'
            preamble.extend(f'~DU{name},{len(data)},'.encode() + data.hex().upper().encode())
            if len(fid) == 1:
                preamble.extend(f'^CW{fid},{name}'.encode())
    return metadata, bytes(preamble)

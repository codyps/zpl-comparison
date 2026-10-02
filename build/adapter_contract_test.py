"""Run corrected external-library adapters with their declared runtime assets."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops

from benchmarks.accuracy.pixels import sha
from build.render import render


class AdapterContractTest(unittest.TestCase):
    def test_zebrash_family_canvas_ink_and_inverted_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for library in ("zebrash", "zpl-renderer-js", "zebrash-ts"):
                with self.subTest(library=library):
                    for orientation in ("N", "I"):
                        self.run_adapter(root, library,
                                         "^XA^PW120^LL50^PO" + orientation + "^FO10,10^GB20,20,2^FS^XZ",
                                         192, 320, library + orientation)
                    with Image.open(root / (library + "N/image.png")) as normal, Image.open(root / (library + "I/image.png")) as inverted:
                        self.assertGreater(sum(value < 128 for value in normal.convert("L").get_flattened_data()), 0)
                        difference = ImageChops.difference(normal.convert("L").transpose(Image.Transpose.ROTATE_180), inverted.convert("L"))
                        self.assertIsNone(difference.getbbox())

    def test_zebrash_family_probe_and_timing_protocols(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.zpl"
            source.write_text("^XA^FO10,10^GB20,20,2^FS^XZ")
            output = root / "output"
            for library in ("zebrash", "zpl-renderer-js", "zebrash-ts"):
                deployment = Path("library_" + library).resolve()
                command = [str(deployment / arg) if (deployment / arg).exists() else arg
                           for arg in json.loads((deployment / "command.json").read_text())]
                modes = ["png"] if library == "zpl-renderer-js" else ["parse", "png"]
                for mode in modes:
                    with self.subTest(library=library, mode=mode):
                        output.unlink(missing_ok=True)
                        probe_mode = "probe-render" if mode == "png" else "probe-parse"
                        probe = subprocess.run(command + [probe_mode, str(source), "1", str(output)], capture_output=True, text=True, timeout=30, check=True)
                        self.assertEqual(probe.stdout.strip(), "accepted", probe.stderr)
                        timed = subprocess.run(command + [mode, str(source), "2", str(output)], env={**os.environ, "ZPL_BENCH_MEMORY": "1"}, capture_output=True, text=True, timeout=30, check=True)
                        result = json.loads(timed.stdout)
                        self.assertEqual(result["iterations"], 2)
                        self.assertGreater(result["ns"], 0)
                        self.assertGreater(result["checksum"], 0)
                        self.assertGreater(output.stat().st_size, 0)
                        if mode == "png":
                            with Image.open(output) as image:
                                self.assertEqual(image.size, (400, 300))
                if library == "zpl-renderer-js":
                    binary = root / "binary.zpl"
                    binary.write_bytes(b"^XA^FO10,10^GFB,1,1,1,\xff^FS^XZ")
                    probe = subprocess.run(command + ["probe-render", str(binary), "1", str(output)], capture_output=True, text=True, timeout=30, check=True)
                    self.assertEqual(probe.stdout.strip(), "rejected", probe.stderr)

    def run_adapter(self, root, library, source, width, height, suffix):
        path = root / "input.zpl"
        path.write_bytes(source if isinstance(source, bytes) else source.encode())
        images = root / suffix
        metadata = root / (suffix + ".json")
        render(dict(source=str(path), sha256=sha(path), library="library_" + library,
                    width=width, height=height, row={}), metadata, images)
        row = json.loads(metadata.read_text())
        self.assertEqual(row["status"], "rendered", row.get("diagnostic"))
        with Image.open(images / "image.png") as image:
            self.assertEqual(image.size, (width, height))
        return sha(images / "image.png")

    def test_zplr_uses_requested_canvas(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for i, dimensions in enumerate(["", "^PW120^LL50"]):
                self.run_adapter(root, "zplr", "^XA" + dimensions + "^FO10,10^GB20,20,2^FS^XZ",
                                 192, 320, str(i))

    def test_zplr_preserves_binary_graphics_and_utf8_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prefix = "^XA^CI28^FO10,10^A0N,20,15^FDCafé^FS^FO10,60".encode()
            suffix = b"^FS^XZ"
            binary = self.run_adapter(root, "zplr", prefix + b"^GFB,4,4,1,\xff\x81\x81\xff" + suffix, 192, 120, "binary")
            ascii_hex = self.run_adapter(root, "zplr", prefix + b"^GFA,4,4,1,FF8181FF" + suffix, 192, 120, "hex")
            self.assertEqual(binary, ascii_hex)
            with Image.open(root / "binary/image.png") as image:
                # FF,81,81,FF is a visible 8-by-4 frame, not two omitted graphics.
                self.assertEqual(sum(v < 128 for v in image.crop((10, 60, 18, 64)).get_flattened_data()), 20)

    def test_text_adapters_do_not_replace_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.zpl"
            source.write_bytes(b"^XA^FO10,10^FD\xff^FS^XZ")
            for library in ("zplr", "binarykits", "zpl-renderer-js"):
                output, metadata = root / library, root / (library + ".json")
                render(dict(source=str(source), sha256=sha(source), library="library_" + library,
                            width=192, height=120, row={}), metadata, output)
                row = json.loads(metadata.read_text())
                self.assertIn(row["status"], ("error", "crashed"))
                self.assertFalse((output / "image.png").exists())

    def test_binarykits_has_pinned_fonts_without_host_font_discovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = "^XA^FO10,10^A0N,24,16^FDFont zero^FS^FO10,60^AAN,18,10^FDMonospace^FS^XZ"
            normal = self.run_adapter(root, "binarykits", source, 384, 200, "normal")
            config = root / "fonts.conf"
            config.write_text('<?xml version="1.0"?><fontconfig></fontconfig>')
            with patch.dict(os.environ, {"FONTCONFIG_FILE": str(config), "FONTCONFIG_PATH": str(root)}):
                isolated = self.run_adapter(root, "binarykits", source, 384, 200, "isolated")
            self.assertEqual(normal, isolated)
            identities = json.loads(Path("library_binarykits/identity.json").read_text())
            files = {row["name"] for row in identities}
            self.assertIn("fonts/TeX Gyre Heros Cn-Bold.otf", files)
            self.assertIn("fonts/DejaVu Sans Mono.ttf", files)


if __name__ == "__main__":
    unittest.main()

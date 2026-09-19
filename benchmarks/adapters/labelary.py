#!/usr/bin/env python3
"""Replay a hash-verified Labelary response through the accuracy adapter protocol."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labelary import saved_response


def main():
    mode, source, iterations, output, width, height = sys.argv[1:]
    if mode != "accuracy" or iterations != "1":
        raise ValueError(
            "Labelary captures support accuracy only, not performance measurement"
        )
    image = saved_response(Path(source), int(width), int(height))
    Path(output).write_bytes(image.read_bytes())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)

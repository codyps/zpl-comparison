"""Collect timestamped public repository metadata outside the Bazel action graph."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess


def collect(pins):
    data = dict(observed_utc=datetime.now(timezone.utc).isoformat(), repositories={}, errors={})
    for name, source in sorted(pins.items()):
        if name == "zpl":
            continue
        repository = source["url"].removeprefix("https://github.com/").removesuffix(".git")
        try:
            result = json.loads(subprocess.check_output(["gh", "api", "repos/" + repository], text=True, stderr=subprocess.PIPE, timeout=30))
            data["repositories"][repository] = {key: result[key] for key in ["stargazers_count", "forks_count", "pushed_at"]}
        except (subprocess.SubprocessError, OSError, ValueError, KeyError) as error:
            data["errors"][repository] = type(error).__name__
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(collect(json.loads(Path("benchmarks/sources.lock.json").read_text())), indent=2) + "\n")

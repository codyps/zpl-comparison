"""Resolve a trusted published bundle to a pinned URL/hash for a fork preview."""

import argparse
import json
from pathlib import Path
import re
import subprocess


def resolve(repository):
    releases = json.loads(subprocess.check_output(["gh", "api", "repos/" + repository + "/releases?per_page=100"], text=True))
    for release in sorted(releases, key=lambda r: r.get("published_at") or "", reverse=True):
        tag = release["tag_name"]
        if release["draft"] or not re.fullmatch(r"ci-observations-\d+-\d+", tag):
            continue
        assets = {a["name"]: a for a in release["assets"]}
        if not {"observations.tar.gz", "observations.tar.gz.json"}.issubset(assets):
            continue
        lock = json.loads(subprocess.check_output(["gh", "api", "repos/" + repository + "/releases/assets/" + str(assets["observations.tar.gz.json"]["id"]), "-H", "Accept: application/octet-stream"], text=True))
        if lock["schema"] != 1 or lock["kind"] != "bundle" or not re.fullmatch(r"[0-9a-f]{64}", lock["sha256"]):
            raise ValueError("Malformed published baseline lock")
        if lock["strip_prefix"] != "observations" or not re.fullmatch(r"[0-9a-f]{40}", lock["revision"]):
            raise ValueError("Malformed published baseline identity")
        lock["url"] = "https://github.com/" + repository + "/releases/download/" + tag + "/observations.tar.gz"
        return lock
    return json.loads(Path("build/baseline.lock.json").read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(resolve(args.repository), indent=2) + "\n")

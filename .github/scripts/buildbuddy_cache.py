#!/usr/bin/env python3
"""Configure CI caching without putting the BuildBuddy key in Bazel options."""

import json
import os
from pathlib import Path
import shutil
import sys
from urllib.parse import urlsplit

HOST = "remote.buildbuddy.io"
MARKER = "# zpl-comparison CI cache configuration\n"


def configure(home, temporary, api_key):
    home, temporary = Path(home), Path(temporary)
    disk = home / ".cache/bazel-disk"
    disk.mkdir(parents=True, exist_ok=True)
    options = [f"build --disk_cache={disk}"]
    if api_key:
        # Only this directory holds credentials. It is outside the checkout,
        # Bazel outputs, and every uploaded cache/artifact path.
        credentials = temporary / "buildbuddy-credentials"
        credentials.mkdir(mode=0o700, parents=True, exist_ok=True)
        credentials.chmod(0o700)
        key = credentials / "api-key"
        key.write_text(api_key)
        key.chmod(0o600)
        helper = credentials / "helper.py"
        shutil.copyfile(__file__, helper)
        helper.chmod(0o700)
        options += [
            f"common --credential_helper={HOST}={helper}",
            f"build --remote_cache=grpcs://{HOST}",
            "build --remote_upload_local_results=true",
            "build --remote_cache_compression=true",
            # Later shell steps consume these files outside Bazel's graph.
            "build --remote_download_outputs=all",
            "build --remote_timeout=30",
            "build --remote_retries=2",
            f"build --bes_backend=grpcs://{HOST}",
            "build --bes_results_url=https://app.buildbuddy.io/invocation/",
        ]
    rc = home / ".bazelrc"
    original = rc.read_text() if rc.exists() else ""
    # Rerunning setup replaces our section while preserving setup-bazel options.
    original = original.split(MARKER, 1)[0]
    rc.write_text(original.rstrip() + "\n" + MARKER + "\n".join(options) + "\n")
    print("BuildBuddy remote cache and build results enabled." if api_key
          else "BuildBuddy disabled; using the rolling disk cache.")
    return disk


def headers(uri):
    parsed = urlsplit(uri)
    if (parsed.scheme not in {"https", "grpcs"} or parsed.hostname != HOST
            or parsed.port not in {None, 443} or parsed.username or parsed.password):
        return {}
    return {"x-buildbuddy-api-key": [Path(__file__).with_name("api-key").read_text()]}


if __name__ == "__main__":
    if sys.argv[1:] == ["get"]:
        print(json.dumps({"headers": headers(json.load(sys.stdin)["uri"])}))
    elif sys.argv[1:] == ["configure"]:
        disk = configure(Path.home(), os.environ["RUNNER_TEMP"],
                         os.environ.get("BUILDBUDDY_API_KEY", ""))
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"disk-cache={disk}\n")
            output.write(f"remote-enabled={'true' if os.environ.get('BUILDBUDDY_API_KEY') else 'false'}\n")
    else:
        raise SystemExit("Usage: buildbuddy_cache.py configure|get")

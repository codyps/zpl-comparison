#!/usr/bin/env python3
"""Configure Bazel's host-local cache and provide credentials without logging them."""
import base64
import hashlib
import json
import os
from pathlib import Path
import ssl
import sys
import time
import urllib.error
import urllib.request

def open_with_retries(request, context):
    """Bound optional-cache outages; never disable TLS verification."""
    for attempt in range(3):
        try:
            return urllib.request.urlopen(request, context=context, timeout=15)
        except urllib.error.HTTPError as error:
            if error.code < 500:
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        if attempt < 2:
            time.sleep(2 ** (attempt + 1))
    return None


ENDPOINT = "https://10.77.0.1:9443/zpl-comparison"


def headers(credential):
    return {"Authorization": ["Basic " + base64.b64encode(credential.encode()).decode()]}


def persistent_disk():
    # This path must be a host-backed filesystem mount, never the VM root disk.
    mount = Path("/var/cache/bazel-persistent")
    if not mount.is_mount():
        raise RuntimeError(f"{mount} is not mounted; refusing an ephemeral disk cache")
    disk = mount / "zpl-comparison" / "actions"
    disk.mkdir(parents=True, exist_ok=True)
    with (Path.home() / ".bazelrc").open("a") as rc:
        rc.write(f"\nbuild --disk_cache={disk}\n")
        rc.write("build --experimental_disk_cache_gc_max_size=40G\n")
        rc.write("build --experimental_disk_cache_gc_max_age=14d\n")
    print(f"Persistent disk cache configured: {disk}")
    return disk


def configure():
    credential = os.environ.get("WARBLER_CACHE_CREDENTIAL", "")
    if not credential:
        print("No cache credential available; building without the Warbler cache.")
        return
    script = Path(__file__).resolve()
    cert = script.parent.parent / "warbler-cache.crt"
    context = ssl.create_default_context(cafile=str(cert))
    auth = {key: values[0] for key, values in headers(credential).items()}
    empty = hashlib.sha256(b"").hexdigest()
    request = urllib.request.Request(f"{ENDPOINT}/cas/{empty}", headers=auth)
    try:
        response = open_with_retries(request, context)
    except urllib.error.HTTPError:
        response = None
    if response is None:
        print("::warning::Warbler cache unavailable; building uncached.")
        return
    with response:
        assert response.status == 200
    # Verify server-side denial, not merely the client upload setting.
    writer = credential.startswith("writer:")
    if not writer:
        request = urllib.request.Request(f"{ENDPOINT}/cas/{empty}", data=b"", headers=auth, method="PUT")
        try:
            response = open_with_retries(request, context)
            if response is None:
                print("::warning::Warbler cache unavailable; building uncached.")
                return
        except urllib.error.HTTPError as error:
            if error.code not in (401, 403):
                raise
        else:
            raise RuntimeError("Read-only cache credential unexpectedly permits writes")
    script.chmod(0o755)
    with (Path.home() / ".bazelrc").open("a") as rc:
        rc.write(f"\nbuild --remote_cache={ENDPOINT}\n")
        rc.write(f"build --tls_certificate={cert}\n")
        rc.write(f"build --credential_helper=10.77.0.1={script}\n")
        rc.write(f"build --remote_upload_local_results={'true' if writer else 'false'}\n")
        rc.write("build --remote_timeout=60\n")
    print(f"Warbler cache verified: {'read/write' if writer else 'read-only (PUT denied)'}, VM {os.uname().nodename}")


if __name__ == "__main__":
    if sys.argv[1:] == ["get"]:
        request = json.load(sys.stdin)
        # Do not disclose credentials to any other endpoint.
        if request["uri"] == ENDPOINT or request["uri"].startswith(ENDPOINT + "/"):
            print(json.dumps({"headers": headers(os.environ["WARBLER_CACHE_CREDENTIAL"])}))
        else:
            print(json.dumps({"headers": {}}))
    elif sys.argv[1:] == ["configure"]:
        configure()
    elif sys.argv[1:] == ["configure-persistent"]:
        persistent_disk()
        configure()
    else:
        raise SystemExit("Usage: warbler_cache.py configure|configure-persistent|get")

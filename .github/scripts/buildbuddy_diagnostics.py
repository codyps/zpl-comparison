"""Fetch action-cache metadata for report assembly without exposing credentials."""

import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import uuid


def collect(invocation, api_key):
    invocation = str(uuid.UUID(invocation))
    results = []
    token = ""
    while True:
        body = {
            "invocationId": invocation,
            "pageToken": token,
            "filter": {"mask": "search,cacheType", "search": "ZplStage", "cacheType": "AC"},
        }
        request = urllib.request.Request(
            "https://app.buildbuddy.io/rpc/BuildBuddyService/GetCacheScoreCard",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "x-buildbuddy-api-key": api_key},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            page = json.load(response)
        results.extend(page.get("results", []))
        token = page.get("nextPageToken", "")
        if not token:
            return {"invocationId": invocation, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invocations", required=True, help="Comma-separated invocation UUIDs")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    ids = [str(uuid.UUID(value.strip())) for value in args.invocations.split(",")]
    args.output.mkdir(parents=True, exist_ok=True)
    for invocation in ids:
        try:
            result = collect(invocation, os.environ["BUILDBUDDY_API_KEY"])
        except urllib.error.HTTPError as error:
            # Never dump request headers or credentials in CI output.
            raise SystemExit(f"BuildBuddy metadata request failed: HTTP {error.code}") from None
        (args.output / (invocation + ".json")).write_text(json.dumps(result, indent=2) + "\n")
        print(f"{invocation}: {len(result['results'])} cache requests")

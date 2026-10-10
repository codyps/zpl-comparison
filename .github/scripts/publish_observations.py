"""Publish observation releases only while the build is current on main."""

import os
import subprocess


def main_head(repository):
    return subprocess.check_output(
        ["gh", "api", f"repos/{repository}/git/ref/heads/main", "--jq", ".object.sha"],
        text=True,
    ).strip()


def publish(repository, revision, run_id, attempt, server_url):
    def superseded():
        if main_head(repository) == revision:
            return False
        print("Skipped observation release: main advanced beyond this build; "
              "the observation-bundle workflow artifact remains available.")
        return True

    if superseded():
        return False
    subprocess.run([
        "gh", "run", "download", run_id, "--repo", repository,
        "--name", "observation-bundle", "--dir", "bundle",
    ], check=True)
    if superseded():
        return False
    tag = f"ci-observations-{run_id}-{attempt}"
    result = subprocess.run([
        "gh", "release", "create", tag,
        "bundle/observations.tar.gz", "bundle/observations.tar.gz.json",
        "--repo", repository, "--target", revision,
        "--title", f"CI observations {revision}",
        "--notes", f"Hash-verified renderer observations from {server_url}/{repository}/actions/runs/{run_id}. "
        "Retained for fork and offline replay.",
        "--prerelease", "--latest=false",
    ], text=True, capture_output=True)
    # main can advance between the check and tag creation. GITHUB_TOKEN cannot
    # tag an old commit with different workflows. Do not hide other failures.
    if (result.returncode and "HTTP 403: Resource not accessible by integration" in result.stderr
            and superseded()):
        return False
    print(result.stdout, end="")
    print(result.stderr, end="")
    result.check_returncode()
    return True


if __name__ == "__main__":
    publish(os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"],
            os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"],
            os.environ["GITHUB_SERVER_URL"])

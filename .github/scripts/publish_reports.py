"""Publish an output snapshot with history independent of the source branch."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

BRANCH = "refs/heads/generated"
NAME = "github-actions[bot]"
EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"


def git(repo, *args, check=True, env=None):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        env=env,
        text=True,
        capture_output=True,
    )


def remote_head(repo, ref):
    result = git(repo, "ls-remote", "--exit-code", "origin", ref, check=False)
    if result.returncode == 2:
        return None
    result.check_returncode()
    return result.stdout.split()[0]


def publish(repo, output, source_sha, run_url=""):
    repo, output = repo.resolve(), output.resolve()
    if git(repo, "rev-parse", "HEAD").stdout.strip() != source_sha:
        raise ValueError("Source revision does not match the checkout")
    if remote_head(repo, "refs/heads/main") != source_sha:
        print("Skipped publication: main has advanced beyond this build.")
        return None
    for required in (
        "README.md",
        "docs/benchmarks/README.md",
        "docs/benchmarks/accuracy/accuracy.svg",
    ):
        if not (output / required).is_file():
            raise ValueError(f"Incomplete report tree: missing {required}")
    if (output / ".git").exists() or (output / ".github").exists():
        raise ValueError("The report tree must not contain Git metadata or workflows")
    if any(path.is_symlink() for path in output.rglob("*")):
        raise ValueError("The report tree must contain files, not symlinks")

    parent = remote_head(repo, BRANCH)
    if parent:
        git(repo, "fetch", "--no-tags", "origin", BRANCH)
        parent = git(repo, "rev-parse", "FETCH_HEAD").stdout.strip()
        ancestry = git(repo, "merge-base", source_sha, parent, check=False)
        if ancestry.returncode == 0:
            raise ValueError("generated shares source history; refusing to replace it")
        if ancestry.returncode != 1:
            ancestry.check_returncode()

    with tempfile.TemporaryDirectory(prefix="publish-reports-") as tmp:
        env = dict(
            os.environ,
            GIT_DIR=git(repo, "rev-parse", "--absolute-git-dir").stdout.strip(),
            GIT_WORK_TREE=str(output),
            GIT_INDEX_FILE=str(Path(tmp) / "index"),
            GIT_AUTHOR_NAME=NAME,
            GIT_AUTHOR_EMAIL=EMAIL,
            GIT_COMMITTER_NAME=NAME,
            GIT_COMMITTER_EMAIL=EMAIL,
        )
        git(output, "read-tree", "--empty", env=env)
        git(output, "add", "--all", "--force", "--", ".", env=env)
        tree = git(output, "write-tree", env=env).stdout.strip()
        if (
            parent
            and git(repo, "rev-parse", f"{parent}^{{tree}}").stdout.strip() == tree
        ):
            print("Reports are unchanged; generated already contains this output.")
            return parent
        args = ["commit-tree", tree]
        if parent:
            args += ["-p", parent]
        args += ["-m", f"Generate reports from {source_sha}"]
        if run_url:
            args += ["-m", f"Build: {run_url}"]
        commit = git(output, *args, env=env).stdout.strip()

    if remote_head(repo, "refs/heads/main") != source_sha:
        print("Skipped publication: main advanced while preparing the snapshot.")
        return None
    # No force push: a competing publisher must never lose its update.
    git(repo, "push", "origin", f"{commit}:{BRANCH}")
    print(f"Published `{commit}` to `generated` from source `{source_sha}`.")
    return commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-url", default="")
    args = parser.parse_args()
    try:
        publish(Path.cwd(), args.output, args.source_sha, args.run_url)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.stderr or str(exc)) from exc


if __name__ == "__main__":
    main()

"""Run the benchmarks/ unit tests against the checked-out source tree.

`bazel run //:benchmark_tests` supplies the pinned interpreter and report
dependencies; the tests read fixtures and evidence from the workspace itself,
so they are not copied into runfiles. test_zplkit has its own Bazel py_test.
"""

import os
import sys
import unittest
from pathlib import Path

EXCLUDED = {"test_zplkit"}


def main():
    root = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY") or Path(__file__).resolve().parents[1])
    benchmarks = root / "benchmarks"
    os.chdir(root)
    sys.path[:0] = [str(benchmarks), str(root)]
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(
        loader.loadTestsFromName(path.stem)
        for path in sorted(benchmarks.glob("test_*.py"))
        if path.stem not in EXCLUDED
    )
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()

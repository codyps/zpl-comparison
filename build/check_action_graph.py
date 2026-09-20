"""Assert real Bazel action dependencies preserve per-library/per-image caching.

Usage: bazel aquery 'mnemonic("Zpl(Render|Compare|LibraryBuild)", deps(//:reports))'
       --output=jsonproto --include_commandline=false > actions.json
       python3 build/check_action_graph.py actions.json
"""

import functools
import json
import sys
from pathlib import Path


def verify(graph):
    fragments = {p["id"]: p for p in graph["pathFragments"]}

    @functools.cache
    def path(identifier):
        fragment = fragments[identifier]
        parent = fragment.get("parentId")
        return (path(parent) + "/" if parent else "") + fragment["label"]

    artifacts = {a["id"]: path(a["pathFragmentId"]) for a in graph["artifacts"]}
    sets = {d["id"]: d for d in graph["depSetOfFiles"]}

    @functools.cache
    def inputs(identifier):
        entry = sets[identifier]
        return frozenset(
            artifacts[a] for a in entry.get("directArtifactIds", [])
        ) | frozenset().union(
            *(inputs(i) for i in entry.get("transitiveDepSetIds", []))
        )

    counts = {}
    for action in graph["actions"]:
        kind = action["mnemonic"]
        counts[kind] = counts.get(kind, 0) + 1
        files = frozenset().union(
            *(inputs(i) for i in action.get("inputDepSetIds", []))
        )
        outputs = [artifacts[i] for i in action.get("outputIds", [])]
        if kind == "ZplRender":
            sources = [p for p in files if p.endswith(".zpl")]
            assert len(sources) == 1, (
                outputs,
                "render must read one ZPL input",
                sources,
            )
            libraries = [p for p in files if "/bin/library_" in p]
            assert len(libraries) <= 1, (
                outputs,
                "render depends on unrelated libraries",
                libraries,
            )
            if libraries:
                assert not any(
                    p.endswith(".png")
                    and p.startswith(
                        ("benchmarks/accuracy/", "references/", "docs/benchmarks/")
                    )
                    for p in files
                ), (
                    outputs,
                    "local render depends on printer image",
                )
            else:
                assert "labelary" in outputs[0], (
                    outputs,
                    "local render has no compiled library",
                )
        elif kind == "ZplCompare":
            assert not any("/bin/library_" in p for p in files), (
                outputs,
                "comparison directly depends on compilation",
            )
            assert len([p for p in files if p.endswith(".render")]) == 1, (
                outputs,
                "comparison must consume exactly one render",
            )
        elif kind == "ZplLibraryBuild":
            library = Path(outputs[0]).name
            if library != "library_codyps-zpl":
                assert not any("/benchmarks/_work/zpl/" in p for p in files), (
                    library,
                    "unrelated private source dependency",
                )
            if library == "library_go-native":
                assert not any("benchmarks/adapters/go/" in p for p in files), (
                    "Go shared library depends on adapter source"
                )
    assert counts.get("ZplLibraryBuild") == 8, counts
    assert counts.get("ZplRender", 0) > 0, counts
    assert counts.get("ZplCompare") == counts["ZplRender"], counts
    return counts


if __name__ == "__main__":
    print(json.dumps(verify(json.loads(Path(sys.argv[1]).read_text())), sort_keys=True))

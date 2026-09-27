"""Assert real Bazel action dependencies preserve per-library/per-image caching.

Usage: bazel aquery 'mnemonic("Zpl(Render|Compare|LibraryBuild)", deps(//:reports))'
       --output=jsonproto --include_commandline=false > actions.json
       python3 build/check_action_graph.py actions.json
"""

import functools
import json
import sys
from pathlib import Path


LAYOUT_LIBRARIES = {"codyps-zpl", "labelize", "forge", "go", "ffi", "binarykits", "zplr", "labelary"}


def verify_layout_matrix(renders, comparisons, cases):
    expected = {f"{case}-{library}" for case in cases for library in LAYOUT_LIBRARIES}
    for kind, actual in [("renders", renders), ("printer comparisons", comparisons)]:
        assert set(actual) == expected and len(actual) == len(expected), (
            "Incomplete font-free layout " + kind,
            sorted(expected - set(actual)),
            sorted(set(actual) - expected),
        )


def verify(graph, layout_cases=(), saved=False, zq610_cases=()):
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
    layout_renders, layout_comparisons = [], []
    zq610_renders, zq610_comparisons = [], []
    for action in graph["actions"]:
        kind = action["mnemonic"]
        counts[kind] = counts.get(kind, 0) + 1
        files = frozenset().union(
            *(inputs(i) for i in action.get("inputDepSetIds", []))
        )
        outputs = [artifacts[i] for i in action.get("outputIds", [])]
        prefix = "reports_saved_actions" if saved else "reports_actions"
        zq610_outputs = [p for p in outputs if "/" + prefix + "/zq610-candidates/" in p]
        if zq610_outputs and kind in ["ZplRender", "ZplSaved"]:
            zq610_renders.append(next(Path(p).name.removesuffix(".render.json") for p in zq610_outputs if p.endswith(".render.json")))
        elif zq610_outputs and kind == "ZplCompare":
            zq610_comparisons.append(next(Path(p).name.removesuffix(".comparison.json") for p in zq610_outputs if p.endswith(".comparison.json")))
            assert len([p for p in files if p.endswith(".png") and p.startswith(("references/zq610-plus-v1/", "references/zq610-candidates/smoke-"))]) == 1, (outputs, "missing native ZQ610 reference")
        layout_outputs = [p for p in outputs if "/" + prefix + "/layout-accuracy/" in p]
        if layout_outputs and kind in ["ZplRender", "ZplSaved"]:
            name = next(Path(p).name.removesuffix(".render.json") for p in layout_outputs if p.endswith(".render.json"))
            layout_renders.append(name)
            if not saved:
                assert any(p.startswith("test-data/layout-accuracy/cases/") for p in files), (name, "missing layout source")
        elif layout_outputs and kind == "ZplCompare":
            name = next(Path(p).name.removesuffix(".comparison.json") for p in layout_outputs if p.endswith(".comparison.json"))
            layout_comparisons.append(name)
            library = next(lib for lib in LAYOUT_LIBRARIES if name.endswith("-" + lib))
            case = name.removesuffix("-" + library)
            assert "benchmarks/accuracy/layout-reference/" + case + ".png" in files, (name, "missing printer reference")
        if kind == "ZplSaved":
            assert not any("/bin/library_" in p or p.endswith("/results.json") for p in files), (outputs, "saved import depends on compilation or whole results document")
            images = [p for p in files if p.endswith(".png")]
            assert len(images) <= 1, (outputs, "saved import depends on unrelated images")
            assert all(p.startswith(("docs/benchmarks/", "references/zq610-candidates/saved/images/")) for p in images), (outputs, "saved import depends on printer evidence")
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
            if library in ["library_go", "library_go-native"]:
                assert not any(
                    "+go_inputs/" in p
                    and any(
                        part in p
                        for part in ["/go-home/", "/home/", "/modules/cache/download/sumdb/"]
                    )
                    for p in files
                ), (library, "Go build depends on mutable download bookkeeping")
            if library != "library_codyps-zpl":
                assert not any("/benchmarks/_work/zpl/" in p for p in files), (
                    library,
                    "unrelated private source dependency",
                )
            if library == "library_go-native":
                assert not any("benchmarks/adapters/go/" in p for p in files), (
                    "Go shared library depends on adapter source"
                )
    if saved:
        assert counts.get("ZplLibraryBuild", 0) == 0, counts
        assert counts.get("ZplRender", 0) == 0, counts
        assert counts.get("ZplReports", 0) == 0, counts
    else:
        assert counts.get("ZplLibraryBuild") == 8, counts
    observation = "ZplSaved" if saved else "ZplRender"
    assert counts.get(observation, 0) > 0, counts
    assert counts.get("ZplCompare") == counts[observation], counts
    if layout_cases:
        verify_layout_matrix(layout_renders, layout_comparisons, layout_cases)
    if zq610_cases:
        expected = {f"{case}-{lib}" for case in zq610_cases for lib in LAYOUT_LIBRARIES}
        for rows in (zq610_renders, zq610_comparisons):
            assert len(rows) == len(expected) and set(rows) == expected, "Incomplete ZQ610 renderer/reference matrix"
    return counts


if __name__ == "__main__":
    cases = [case["name"] for case in json.loads(Path(sys.argv[2]).read_text())["cases"]] if len(sys.argv) > 2 else []
    print(json.dumps(verify(json.loads(Path(sys.argv[1]).read_text()), cases, saved="--saved" in sys.argv[3:]), sort_keys=True))

# Comparison site

The public artifact contains only HTML, CSS, JavaScript and selected downloadable
evidence. It has one overview, `categories/`, `libraries/`, `cases/`, and a flat
content-addressed `assets/` directory. URLs are relative, so project Pages paths,
local previews and downloaded artifacts work without a configured base URL.
No frontend framework or client-side routing is required. Pillow produces shared ink crops; its version is pinned with the report dependencies.

## Generate from saved evidence

```sh
bazelisk build //:reports_saved
bazelisk run //:comparison_site -- --input "$PWD/bazel-bin/reports_saved" --output "$PWD/_site"
python3 -m http.server 8000 --directory _site
```

Choose an empty output directory; generation refuses to overwrite existing files.
For current local renderer observations, use `//:reports` and `bazel-bin/reports`.
Generation never runs a renderer or relabels saved measurements as fresh. CI stages fresh `//:performance` results into the report tree before site generation. Local report builds and fork previews have no performance measurements unless explicitly supplied.

```sh
bazelisk test //:site_test
```

Every generation checks all local links, fragment destinations and image references.
Missing required evidence fails publication. Blank/missing references and failed
observations retain each suite's score policy. Averages never merge unlike suites.
Case pages use original image dimensions for overlays; all preview images use a common ink bounding box with an eight-pixel margin.
The Full canvas toggle restores originals; scores never use cropped pixels. Source-review claims stay in `examination.html`.

## GitHub Pages

The comparison workflow builds and validates the site on pull requests, uploads a
preview artifact, and deploys main with the official Pages artifact/deployment
actions. In repository **Settings → Pages → Build and deployment**, select
**GitHub Actions** once. The `github-pages` environment must allow `main`.
The workflow no longer writes generated Markdown to a branch. The historical
`generated` branch is left intact so existing evidence links are not destroyed.

[GitHub's custom workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
describes the deployment permissions and environment.

Legacy Markdown generators remain intermediate report producers, not public site
content. This preserves independent measurement/cache boundaries during migration;
the site explicitly selects JSON and image inputs instead of copying those pages.

Published builds (pushes to main, manual runs on main, and the daily 08:23 UTC
schedule) check out the current `codyps/zpl` main once, then record its exact SHA
and package version before building. Cargo retains existing dependency resolutions
where compatible and resolves changes required by that checkout. Both resolved
lock files are uploaded as the `resolved-source-pins` artifact. Pull requests and
local builds retain the checked-in revision. Saved observations keep their original
version provenance; refreshing a build does not relabel historical measurements.

Performance pages generate latency and peak RSS bars directly from saved JSON, grouped by operation and workload. Select table headings to sort ascending or descending. Adapter builds record source bytes, physical lines and file hashes alongside deployed artifact bytes; shared runtimes are excluded.

The October 2026 public-document campaign compares dated zpl and Labelary outputs
against the ZD621. Its saved sources, printer/service captures, renders and
differences are validated during report assembly. The measured zpl revision and
Labelary capture time are shown on every case; rebuilding other suites does not
relabel these observations as fresh. See
[the campaign](../test-data/public-zpl/README.md) to measure another revision.

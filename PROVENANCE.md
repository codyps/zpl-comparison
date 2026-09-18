# Setup and provenance

This comparison suite was extracted from [codyps/zpl](https://github.com/codyps/zpl) on 2026-09-18. Its first standalone source pin is `280fc0cf4d0a49c916463d936e4307a2a226928e`. The original library remains a separate dependency; its source is fetched into the ignored `benchmarks/_work/zpl` directory. Local setup uses your existing GitHub SSH access.

## GitHub Actions secret

The source repository is private. Create a [fine-grained personal access token](https://github.com/settings/personal-access-tokens/new) with resource owner `codyps`, repository access limited to `zpl`, and repository **Contents: Read-only** permission. Choose an expiration and save the token as the repository Actions secret **ZPL_SOURCE_TOKEN** in [Settings → Secrets and variables → Actions](https://github.com/codyps/zpl-comparison/settings/secrets/actions). Do not commit it. The workflow uses it only to check out the pinned source and does not persist checkout credentials. Rotate the secret when its token expires.

## Historical evidence

The initial performance, accuracy and conformance JSON files record runs performed before extraction. Their timestamps, host information and measurements remain historical evidence; moving these files does not constitute a fresh benchmark run. Printer fixtures are copied unchanged into `references/barcodes-zd621-v1`. Conformance manifest source paths and its recorded hash were updated for that relocation only; the ZPL case bytes are unchanged.

The suite and harness retain the original repository's OSL-3.0 license in LICENSE. The bundled Zebra Programming Guide retains Zebra's copyright and notices. Third-party library source is downloaded separately at revisions recorded in `benchmarks/sources.lock.json`; each library retains its own license.

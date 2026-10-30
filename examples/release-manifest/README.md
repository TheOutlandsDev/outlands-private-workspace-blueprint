# Fictional exact-file release tools

These offline tools create and verify a manifest for a small, frozen export.
The allowlist and manifest stay **outside** the export directory. The checked-in
example uses only fictional bytes. From the repository root, choose a fresh
output directory and run:

```sh
output_dir="$(mktemp -d)"
python3 -I -B examples/release-manifest/create_manifest.py examples/release-manifest/fixtures/allowlist.example.json examples/release-manifest/fixtures/export "$output_dir/manifest.json"
python3 -I -B examples/release-manifest/verify_release.py "$output_dir/manifest.json" examples/release-manifest/fixtures/export
python3 -I -B -m unittest discover -s examples/release-manifest -p 'test_*.py'
```

The creator requires a human-written JSON allowlist with `schema_version: 1`
and a sorted `paths` array. It rejects missing, unlisted, linked, oversized and
special files. It refuses an output path inside the export or an existing output
file. Successful output is created with owner-only permissions. If a write fails,
inspect the output path before trying a new destination; a partial file may remain.
The CLI reports only fixed status/error codes, without paths or file contents.

The manifest contains `schema_version: 1` and a sorted `files` array. Each entry
has a relative `path`, integer `bytes`, and lowercase SHA-256 `sha256`. All files
must be listed exactly once. The verifier rejects path traversal, links, special
files, missing or extra files, size changes, and hash changes. It accepts a
manifest up to 64 KiB, up to 128 listed files, 2 MB per file and 8 MB total;
directory traversal stops after 256 entries. Paths use
ASCII letters, digits, dots, underscores, and hyphens in each segment.

Run both tools against an export that nobody is changing. The generated manifest
contains relative file names and hashes, so review it before sharing it. A
`CREATED` or `PASS` result is a byte and shape check for that one local export.
Neither tool reviews private data, provenance, license rights, malware, runtime
behavior, or publication permission. Both outputs keep `privacy_cleared` and
`rights_cleared` false.

The [worked example](../../docs/24-fictional-release-walkthrough.md) shows the
commands, a refusal case, and the separate human review gates.

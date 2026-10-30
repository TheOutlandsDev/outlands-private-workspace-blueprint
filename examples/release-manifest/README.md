# Fictional exact-file release verifier

This offline example checks a small, frozen export against a manifest kept **outside**
the export directory. It uses only fictional bytes. Run it from the repository root:

```sh
python3 -I -B examples/release-manifest/verify_release.py examples/release-manifest/fixtures/manifest.example.json examples/release-manifest/fixtures/export
python3 -I -B -m unittest discover -s examples/release-manifest -p 'test_*.py'
```

The manifest contains `schema_version: 1` and a sorted `files` array. Each entry
has a relative `path`, integer `bytes`, and lowercase SHA-256 `sha256`. All files
must be listed exactly once. The verifier rejects path traversal, links, special
files, missing or extra files, size changes, and hash changes. It accepts a
manifest up to 64 KiB, up to 128 listed files, 2 MB per file and 8 MB total;
directory traversal stops after 256 entries. Paths use
ASCII letters, digits, dots, underscores, and hyphens in each segment.

Run it against an export that nobody is changing during verification. Failure
output contains a fixed code, without file names or file contents. A PASS is a
byte and shape check for that one local export. It does **not** review private
data, provenance, license rights, malware, runtime behavior, or publication
permission. The output keeps `privacy_cleared` and `rights_cleared` false.

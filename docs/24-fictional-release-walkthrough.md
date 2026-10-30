# Worked example: a fictional release export

This walkthrough uses one invented text file to show the path from an explicit
allowlist to a checked manifest. It does not package a server directory, publish
to GitHub, or approve the file for release. Run the commands from the repository
root on a checkout with Python 3.9 or newer.

## 1. Select the exact file

The [example export](../examples/release-manifest/fixtures/export/example.txt)
contains one 46-byte file with fictional text. The human-written
[allowlist](../examples/release-manifest/fixtures/allowlist.example.json) names
only `example.txt`. Keep an allowlist outside the export so the tools can reject
any unexpected file inside it.

| Selected path | Size | SHA-256 in the checked-in manifest |
| --- | ---: | --- |
| `example.txt` | 46 bytes | `42ebd053d2467f487161a874b34eafb91a0dcd8432e6aa545f708685a2c9add4` |

The hash identifies these bytes. It says nothing about whether the text is safe
or legally yours to publish.

## 2. Create, then verify

Choose a fresh output directory. The creator refuses an existing output file and
keeps the generated manifest outside the export:

```sh
review_dir="$(mktemp -d)"
python3 -I -B examples/release-manifest/create_manifest.py examples/release-manifest/fixtures/allowlist.example.json examples/release-manifest/fixtures/export "$review_dir/manifest.json"
python3 -I -B examples/release-manifest/verify_release.py "$review_dir/manifest.json" examples/release-manifest/fixtures/export
```

Expected output for this unchanged fictional fixture:

```json
{"bytes_checked": 46, "files_checked": 1, "privacy_cleared": false, "result": "CREATED", "rights_cleared": false}
{"bytes_checked": 46, "files_checked": 1, "privacy_cleared": false, "result": "PASS", "rights_cleared": false}
```

The creator checks the selected file and rejects extra files, links and special
files. The verifier checks the manifest against the export again. Both need an
export that remains unchanged while they run. The manifest itself contains file
names and hashes; keep it private until its contents are reviewed.

## 3. Observe a refusal on a disposable copy

This optional drill changes only a copy of the fictional fixture. It adds an
unlisted file and asks the creator for a new output path:

```sh
cp -a examples/release-manifest/fixtures/export "$review_dir/changed-export"
printf 'fictional extra\n' > "$review_dir/changed-export/extra.txt"
python3 -I -B examples/release-manifest/create_manifest.py examples/release-manifest/fixtures/allowlist.example.json "$review_dir/changed-export" "$review_dir/rejected.json"
```

The last command exits with status 2 and prints `ERROR: EXTRA_FILE`. It creates
no `rejected.json`. Keep the failed observation; do not change the allowlist just
to make an unexpected file pass.

## 4. Make the publication decision separately

For this teaching run, the record is deliberately incomplete:

| Gate | Example status | What remains |
| --- | --- | --- |
| Exact file and hash | PASS | The tools checked one frozen fictional export. |
| Content and metadata privacy review | NOT RUN | Inspect every selected file and generated output. |
| Provenance, license and notices | NOT RUN | Establish rights and retain required notices. |
| Destination and history review | NOT RUN | Check visibility, diff, commit metadata and old history. |
| Publication decision | HOLD | The owner decides after the independent reviews. |

For a different export, follow the [public export review](22-publication-review.md):
record an exact allowlist and hashes privately, review content and rights, run
the repository checks, then compare the final remote bytes after an authorized
publication. A successful `CREATED` or `PASS` result never changes the privacy
or rights gates to PASS.

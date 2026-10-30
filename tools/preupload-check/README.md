# Pre-upload review aid

A public pull request branch exposes its files before CI starts. This offline
command checks a frozen, exact-file **text** export before the first push. It
does not contact GitHub, make a commit, or decide that publication is safe.

## Try the fictional export

From the repository root:

```sh
receipt_parent="$(mktemp -d)"
cp tools/preupload-check/fixtures/private-terms.example.json "$receipt_parent/private-terms.json"
chmod 600 "$receipt_parent/private-terms.json"
python3 -I -B tools/preupload-check/preupload_check.py \
  tools/preupload-check/fixtures/allowlist.example.json \
  tools/preupload-check/fixtures/export \
  tools/preupload-check/fixtures/base-paths.example.json \
  "$receipt_parent/private-terms.json" \
  "$receipt_parent/fictional-receipt"
python3 -I -B -m unittest discover -s tools/preupload-check -p 'test_*.py'
```

The command prints a fixed status and creates `report.json`, `REVIEW.md`, and
`REVIEW.txt` in a new 0700 receipt directory. The files are mode 0600 and
contain relative paths and hashes. Keep a real receipt private. Inspect a
failed or partial receipt before trying a new directory name.

## Prepare a real review

1. Copy only proposed public files into a fresh staging directory. Keep the
   allowlist, base-path inventory, private terms file, and receipts **outside**
   that directory and outside any public repository branch.
2. Review and write a sorted JSON allowlist in the example format. Bind each
   path to its expected SHA-256. `synthetic_fixture` identifies files that need
   a separate human check; it does not prove they are fictional.
3. Read the intended base commit and its file-path tree from the destination.
   Put that commit and sorted file paths in the base-path inventory. The tool
   compares the two supplied commit IDs but cannot authenticate GitHub state.
4. Create your own owner-only (0600) private terms file. Include sensitive provider,
   destination, host, person, project, and account strings or aliases relevant
   to your export. The fictional public example is not a real denylist. The
   tool never prints matched values or saves the terms file in its receipt.
5. Create an empty receipt parent owned by you with mode 0700, then choose a
   new receipt child name. Run the command before pushing any branch. If the
   staged bytes change, repeat the checks and review.

The command rejects extra or missing paths, changed hashes, symlinks,
hardlinks, special files, binaries, selected private file types, common
private-data shapes, and unresolved relative Markdown link **paths**. It has
bounds of 128 files, 256 directory entries, 2 MB per file, and 8 MB total.
It does not check link anchors, web links, images, archives, PDFs, Git history,
or every possible secret. Run the repository's `scripts/check_public_source.py`,
relevant tests, diff review, provenance and rights review, and destination
readback separately. See [publication review](../../docs/22-publication-review.md).

Even when technical checks say `PASS`, every receipt says
`publication_authorized=false` and keeps manual review fields `PENDING`. No
indexed source match or clean pattern scan proves authorship or permission to
release. Never upload the receipt or private terms file as part of an export.

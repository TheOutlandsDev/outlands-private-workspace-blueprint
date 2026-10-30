# Review a public blueprint export

An open source guide is useful when someone else can inspect and try it without receiving the operator's private data. Prepare a fresh export from an exact allowlist. Do not copy a server directory or an internal evidence packet into a repository and rely on an ignore rule to fix the selection.

## Select

Choose only the files needed for a reproducible example: source, documentation, fictional fixtures, tests, and required notices. Record each selected path, byte length, and SHA-256 outside the export. Give each file a reason to be there. Keep real configuration, databases, backups, logs, credentials, account lists, host inventories, private routes, and live screenshots in protected storage. Do not publish an operator's backup provider or any destination identifier, even in a diagram, command, test fixture, or commit message.

Use reserved example domains and fictional names in teaching material. A redacted label or a passing pattern scan does not clear a file. Review text, filenames, diagrams, image/document metadata, embedded assets, links, and generated outputs. Git commits expose author and message metadata; an old secret remains in history even after its latest file is changed. Start with clean history for a new public export.

## Establish rights and provenance

Trace copied or adapted code, images, dependencies, contributor input, and upstream notices. Search the public web using safe filenames or generic naming combinations before posting code. Keep private source and distinctive internal identifiers out of public queries. A search with no match is limited evidence; it does not prove authorship or license rights.

This repository's original material is [MIT licensed](../LICENSE). That license does not relicense upstream applications, their brands, or material taken from a private project. Resolve rights and retain required notices before adding a new source selection.

## Check the exact bytes

1. Review the entire proposed diff and the exact allowlist.
2. Run `python3 -I -B scripts/check_public_source.py` from the repository root. It is a bounded screen, not a guarantee.
3. Run the tests relevant to changed examples and record their output and limits.
4. Inspect files that a text scanner cannot understand, including images, archives, PDF, and office documents, separately.
5. Compare the final file hashes to the reviewed selection. If any file changes, repeat the affected review.
6. Recheck the destination's visibility, branch head, license and notices before publishing. After publishing, read back the exact paths and hashes from the remote repository.

The [Public Release Audit](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/public-release-audit) is another offline text-export screening aid. Its report can contain sensitive filenames and belongs in private review storage. Neither tool checks every possible secret, source right, or Git history.

## Report what was proved

State the exact published paths and commit. Separate syntax checks, fictional demo behavior, native deployment, access denial, physical-device use, and restore acceptance. If a check was blocked or not run, leave it that way. A useful public example can be honest about those limits.

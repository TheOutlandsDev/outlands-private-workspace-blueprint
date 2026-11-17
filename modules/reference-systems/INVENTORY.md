# Bounded source inventory

The scanner counts saved UTF-8 code, configuration and prose independently.
It never executes a source file, emits a filename, infers authorship or reads
outside the selected root. Default use reads only the invented fixture:

```sh
python3 -I -B modules/reference-systems/run.py inventory --demo
```

Expect one code file, one configuration file, one prose file and one excluded
vendor directory. Every report says `PARTIAL_BY_POLICY` and
`authorship_established=false`. Blank and nonblank line counts are separate.

## Optional reader-owned private scan

This is a separate explicit opt-in. Review the scanner, then choose one
reader-owned source root that already has mode 0700 and a separate existing
owner-only report directory. Do not change an existing production directory's
permissions just to try a demo; use a new private test copy if necessary.

From the repository root, with the two variables set privately:

```sh
python3 -I -B modules/reference-systems/run.py inventory \
  --scan-root "$PRIVATE_SOURCE_ROOT" --report "$PRIVATE_REPORT_FILE"
```

Both paths must be absolute, with no symlink aliases. The report must be outside
the source root; its immediate parent must be owned by the caller and mode 0700.
The report file must not already exist. It is created mode 0600. Standard output
contains only fixed success flags; actual counts and UTC observation time stay
in the private report. An error prints a fixed `REVIEW`, never a path or exception.
Keep failed/partial output for inspection and choose a new filename for a retry.

## Inclusion and refusal policy

Code extensions: `.py`, `.js`, `.ts`, `.rs`, `.sh`, `.css`, `.html`.
Configuration: `.json`, `.toml`, `.yaml`, `.yml`. Prose: `.md`, `.txt`.
Hidden files, other extensions, and `.git`, `.secrets`, `.venv`, `__pycache__`,
`node_modules`, `vendor`, `build`, `dist`, and `generated` directories are excluded.
Generated files outside these named directories may still be counted; use an
isolated, reviewed scope and record that limitation.

Traversal is descriptor-relative and refuses symlinks, hardlinked files,
special files, cross-device traversal, binary/invalid UTF-8 included files,
observed changes, excessive depth and oversized reads. Bounds: 512 visited
entries, 128 included files, 64 KiB per included file, 1 MiB included bytes and
16 directory levels. Hitting a limit fails the scan rather than producing a
successful partial count. Policy exclusions still produce a partial-coverage
label; they do not imply complete discovery.

```sh
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_inventory.py'
```

Tests cover count separation, exclusions, path-free reports, links/FIFOs, size
and entry bounds, binary refusal, private permissions and no-overwrite output.
The [descriptor-based traversal approach](https://docs.python.org/3/library/os.html#files-and-directories)
is Linux-specific here. Readability checks are not a source-rights review.

## Maintenance and rollback

The tool installs no daemon or schedule, opens no socket, and modifies no source.
Keep an earlier report and source revision when changing its counting policy.
Rerun fixture tests, compare policy differences privately, and create a fresh
report. Removing a disposable demo copy or private report is a reader decision;
the scanner performs no automatic cleanup or deletion.

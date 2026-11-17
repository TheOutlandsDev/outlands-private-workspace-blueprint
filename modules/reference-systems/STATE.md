# Durable synthetic state and recovery

The workspace can keep fictional documents, their active deletions, and the
selected source-state scenario across restarts. Persistence is explicit. The
default `workspace --serve` command remains memory-only. No real project data,
provider settings, credentials or deployment configuration is imported.

## 1. Initialize a new private state directory

Use Linux, Python 3.10+ and a local filesystem that supports descriptor operations,
file locks, atomic rename and fsync. Select an absolute new directory under an
existing owner-owned mode-0700 parent, outside the source checkout and any Git
repository. Set `PRIVATE_STATE_DIR` privately in your terminal; do not publish it.

From the repository root:

```sh
python3 -I -B modules/reference-systems/run.py state init \
  --directory "$PRIVATE_STATE_DIR"
python3 -I -B modules/reference-systems/run.py state inspect \
  --directory "$PRIVATE_STATE_DIR"
python3 -I -B modules/reference-systems/run.py workspace --serve \
  --state-dir "$PRIVATE_STATE_DIR"
```

Initialization refuses an existing directory. Startup refuses missing, corrupted
or unsupported state; it never silently initializes or resets it. The state root
is mode 0700 and every file mode 0600, owned by the caller. Symlink aliases,
hardlinks, special files, unexpected entries, nested state roots and Git checkout
locations are refused. Empty `.git` permission-marker directories alone are not
Git repositories; populated metadata and `.git` files/symlinks are refused.

Open the printed loopback URL. Use the same public fictional accounts and
password in the [workspace walkthrough](WORKSPACE.md). Owner-only deletion and
source-state forms retain the existing session, CSRF and exact-Origin checks.
The persistent mode saves changes before reporting success. Stop with Ctrl+C,
restart with the same flag, and verify that active deletions and the scenario
remain. Every prior session cookie is denied after restart; sign in again.

Only fictional corpus records, scenario, schema and reset counter are stored.
Session tokens, CSRF values, password digests, salts and accounts are never stored.
The identity demonstration still uses public credentials and loopback HTTP. This
feature does not make it a production authentication boundary.

## 2. Stop, snapshot and restore into a fresh directory

Stop the workspace first. Its exclusive lock prevents a second server or offline
administration command from opening the same state while it is running. Choose
a new absolute `PRIVATE_SNAPSHOT_FILE` under an existing private 0700 parent,
outside Git and outside the state root. Choose a separate new
`PRIVATE_RESTORE_DIR` with an existing private parent.

```sh
python3 -I -B modules/reference-systems/run.py state backup \
  --directory "$PRIVATE_STATE_DIR" --output "$PRIVATE_SNAPSHOT_FILE"
python3 -I -B modules/reference-systems/run.py state restore \
  --input "$PRIVATE_SNAPSHOT_FILE" --directory "$PRIVATE_RESTORE_DIR"
python3 -I -B modules/reference-systems/run.py workspace --serve \
  --state-dir "$PRIVATE_RESTORE_DIR"
```

Backup is a bounded JSON envelope of the active logical state, with a SHA-256
checksum. It contains no file paths, archive members, sessions or history. It
does not name or select a backup provider. No network or external storage is
contacted. Outputs are private and never overwritten. Restore validates the
envelope, checksum, schema and synthetic admission contract before creating a
new directory; it refuses an existing destination. It creates a fresh generation
sequence without changing the source state or snapshot.

Check the restored scenario, permitted document counts, active deletions, owner
and reader denial, and rejection of the old cookie. A post-deletion snapshot
retains the deletion. An older snapshot or rollback can intentionally bring back
earlier fictional records. Deletion here means removal from active state, not
erasure from retained generations, snapshots or storage media. Checksums detect
accidental corruption; they do not authenticate an untrusted source or prove
that declarations of synthetic content and rights are true.

## 3. Versioned upgrade and rollback

State schema 1 stores the fictional corpus and scenario. Schema 2 adds an
explicit reset counter. Current initialization uses schema 2. The recovery
rehearsal constructs schema 1 privately to exercise the upgrade path; no runtime
state file is checked into Git.

`inspect` reports only fixed status, generation and state schema metadata. Use
the reported generation as `EXPECTED_GENERATION` in your private terminal:

```sh
python3 -I -B modules/reference-systems/run.py state upgrade \
  --directory "$PRIVATE_STATE_DIR" --expect-generation "$EXPECTED_GENERATION"
python3 -I -B modules/reference-systems/run.py state rollback \
  --directory "$PRIVATE_STATE_DIR" --to-generation "$PRIOR_GENERATION" \
  --expect-generation "$EXPECTED_GENERATION"
```

Reinspect before each operation. Stale expected generations refuse the change.
Upgrade writes a new generation; it does not overwrite the old one. Upgrade of
current schema reports no change. Rollback verifies the selected earlier snapshot
and publishes its logical state as another new generation. The history never
moves backward or overwrites a file. Rolling back to schema 1 requires another
explicit upgrade before serving with current code. Unknown future schemas are
refused, with no automatic downgrade.

## 4. Explicit reset with preserved history

Reset is an offline command, not a browser action or startup fallback:

```sh
python3 -I -B modules/reference-systems/run.py state reset \
  --directory "$PRIVATE_STATE_DIR" --expect-generation "$EXPECTED_GENERATION" \
  --confirm-reset RESET-SYNTHETIC-STATE
```

It requires current schema, the exact generation and the literal confirmation.
It seeds the original public fixtures in a new active generation and increments
the reset counter. Earlier generations are preserved. It deletes no directory,
snapshot or original file. There is no automated retention cleanup.

## Commit and failure boundaries

Each generation is immutable, privately permissioned, bounded and independently
checksummed. The active pointer also records its generation's hash. New state
and a pending pointer are written and fsynced before atomic pointer replacement;
the directory is then fsynced before acknowledging success. The new directory's
parent is fsynced on initialization. See the Python references for
[atomic replacement and fsync](https://docs.python.org/3/library/os.html#os.replace)
and [advisory file locking](https://docs.python.org/3/library/fcntl.html#fcntl.flock).
Locks coordinate these tools; they do not protect against the account owner or
other programs that ignore the lock. Network filesystems are not qualified.

A failed or conflicting commit makes that running store unavailable. Protected
workspace reads and mutations then return a fixed 503; logout still works.
No exception or private path enters the HTTP response. Memory is changed only
after the store confirms publication. If pointer replacement occurred but its
final fsync failed, the new state may be present despite the failed response.
Stop and inspect privately before deciding to retry. Do not assume failure means
that no on-disk change occurred.

Uncommitted generations/pending heads are preserved and never automatically
promoted. A valid old active pointer can be reopened; new writes use a fresh
generation number. Corrupt or missing active state is refused. Restore a verified
snapshot into a fresh directory rather than deleting or reseeding uncertain data.
Keep the failed directory and snapshot for private review.

Bounds: 64 retained generation files, 130 directory entries, 128 KiB canonical
payload, 16 fictional documents of at most 4096 characters each, and generation
numbers up to one million. Snapshots admit no unknown fields or auth state.
Reaching a limit refuses writes. To start a new history, stop the server, create
a verified snapshot and restore it into a fresh private directory; preserve the
original. Every actual backup path, report and state file remains outside Git.

## Disposable acceptance rehearsal

```sh
python3 -I -B modules/reference-systems/run.py state rehearse
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_state_*.py'
```

The offline rehearsal uses invented fixtures in a new private temporary directory
and removes only that disposable directory on exit. It checks restart, snapshot
restore, schema upgrade/rollback and explicit reset without a socket or subprocess.
Additional tests run actual Python child servers across restart and abrupt exit,
verify old-cookie denial and restored deletion/state, and inject commit failures.
These are process-level synthetic results, not hardware power-loss tests or a
real application restore qualification. Keep real deployment acceptance private
and separate.

import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run
import state_store
from state_commands import handle, rehearsal, reset
from state_store import StateError, StateStore, canonical, restore


class StateStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.directory = self.parent / 'state'

    def create(self, payload=None):
        return StateStore.create(self.directory, payload if payload is not None else run.seed_state())

    def test_private_generations_and_restart_keep_active_deletion(self):
        with self.create() as store:
            payload = store.payload
            payload['scenario'] = 'stale'
            payload['corpus']['documents'] = [d for d in payload['corpus']['documents'] if d['id'] != 'fictional-owner-note']
            store.commit(payload)
            self.assertEqual(store.generation, 2)
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        for file in self.directory.iterdir():self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        with run.workspace_persistent(self.directory).store as store:
            self.assertEqual(store.payload, payload)
            self.assertNotIn('fictional-owner-note', json.dumps(store.payload))

    def test_init_never_replaces_an_existing_directory(self):
        with self.create():pass
        before = (self.directory / 'current.json').read_bytes()
        with self.assertRaises(FileExistsError):self.create()
        self.assertEqual((self.directory / 'current.json').read_bytes(), before)

    def test_exclusive_lock_blocks_second_process_context_and_offline_admin(self):
        with self.create():
            with self.assertRaises(BlockingIOError):StateStore(self.directory)
            with self.assertRaises(BlockingIOError):handle(['inspect', '--directory', str(self.directory)], run.seed_state)

    def test_outside_git_and_private_location_contract(self):
        public = self.parent / 'public'
        public.mkdir(mode=0o755)
        with self.assertRaises(ValueError):StateStore.create(public / 'state', run.seed_state())
        link = self.parent / 'alias'
        link.symlink_to(self.parent, target_is_directory=True)
        with self.assertRaises(ValueError):StateStore.create(link / 'state', run.seed_state())
        with patch.object(state_store, 'CHECKOUT', self.parent):
            with self.assertRaises(ValueError):self.create()
        marker = self.parent / '.git'
        marker.mkdir()
        with self.create():pass  # An empty permission marker is not repository metadata.
        (marker / 'HEAD').write_text('ref: refs/heads/fictional\n')
        with self.assertRaises(ValueError):StateStore(self.directory)

    def test_nested_state_creation_is_refused_without_modifying_parent(self):
        with self.create() as store:
            before = store.generation
            with self.assertRaises(ValueError):StateStore.create(self.directory / 'nested', run.seed_state())
            self.assertFalse((self.directory / 'nested').exists())
            self.assertEqual(store.generation, before)

    def test_permissions_links_and_unknown_entries_fail_closed(self):
        with self.create():pass
        file = self.directory / 'state-00000001.json'
        file.chmod(0o644)
        with self.assertRaises(ValueError):StateStore(self.directory)
        file.chmod(0o600)
        external = self.parent / 'external.json'
        file.rename(external)
        file.symlink_to(external)
        with self.assertRaises(ValueError):StateStore(self.directory)
        file.unlink()
        os.link(external, file)
        with self.assertRaises(ValueError):StateStore(self.directory)
        file.unlink()
        external.rename(file)
        (self.directory / 'unexpected').write_text('fixture')
        with self.assertRaises(ValueError):StateStore(self.directory)

    def test_corrupt_active_state_is_not_reseeded(self):
        with self.create():pass
        file = self.directory / 'state-00000001.json'
        envelope = json.loads(file.read_text())
        envelope['payload']['scenario'] = 'stale'
        file.write_text(json.dumps(envelope))
        before = file.read_bytes()
        with self.assertRaises(ValueError):run.workspace_persistent(self.directory)
        self.assertEqual(file.read_bytes(), before)

    def test_backup_restore_integrity_and_no_overwrite(self):
        snapshot = self.parent / 'snapshot.json'
        with self.create() as store:
            store.backup(snapshot)
            with self.assertRaises(FileExistsError):store.backup(snapshot)
            expected = store.payload
        self.assertEqual(snapshot.stat().st_mode & 0o777, 0o600)
        with restore(snapshot, self.parent / 'restored') as recovered:
            self.assertEqual(recovered.payload, expected)
        with self.assertRaises(FileExistsError):restore(snapshot, self.parent / 'restored')
        envelope = json.loads(snapshot.read_text())
        envelope['payload']['scenario'] = 'unavailable'
        snapshot.write_text(json.dumps(envelope))
        with self.assertRaises(ValueError):restore(snapshot, self.parent / 'bad')
        self.assertFalse((self.parent / 'bad').exists())

    def test_backup_rejects_paths_unknown_fields_and_auth_state(self):
        with self.create() as store:
            for key in ['sessions', 'password_digest', 'path']:
                payload = store.payload
                payload[key] = 'fictional'
                with self.assertRaises(ValueError):store.commit(payload)
            with self.assertRaises(ValueError):store.backup(self.directory / 'backup.json')
        snapshot = self.parent / 'snapshot.json'
        snapshot.write_text(json.dumps({'backup_schema': 1, 'synthetic_fixture': True, 'path': '../fixture'}))
        snapshot.chmod(0o600)
        with self.assertRaises(ValueError):restore(snapshot, self.parent / 'bad')

    def test_explicit_upgrade_rollback_and_reupgrade_preserve_old_generations(self):
        original = run.seed_state()
        original.pop('reset_count')
        original['schema_version'] = 1
        with self.create(original):pass
        with self.assertRaises(StateError):run.workspace_persistent(self.directory)
        with StateStore(self.directory) as store:
            self.assertTrue(store.upgrade(1))
            self.assertEqual(store.generation, 2)
            self.assertFalse(store.upgrade(2))
            store.rollback(1, 2)
            self.assertEqual(store.generation, 3)
            self.assertEqual(store.payload, original)
            self.assertTrue(store.upgrade(3))
        self.assertTrue((self.directory / 'state-00000001.json').exists())
        with StateStore(self.directory) as store:self.assertEqual(store.payload['schema_version'], 2)

    def test_rollback_checks_old_snapshot_checksum(self):
        with self.create() as store:
            payload = store.payload
            payload['scenario'] = 'stale'
            store.commit(payload)
            file = self.directory / 'state-00000001.json'
            envelope = json.loads(file.read_text())
            envelope['payload']['scenario'] = 'unavailable'
            file.write_text(json.dumps(envelope))
            with self.assertRaises(ValueError):store.rollback(1, 2)
            self.assertEqual(store.generation, 2)

    def test_reset_requires_confirmation_and_keeps_history(self):
        with self.create() as store:
            with self.assertRaises(ValueError):reset(store, run.seed_state, 1, 'wrong')
            payload = store.payload
            payload['corpus']['documents'] = []
            store.commit(payload)
            reset(store, run.seed_state, 2, 'RESET-SYNTHETIC-STATE')
            self.assertEqual(store.payload['reset_count'], 1)
            self.assertEqual(len(store.payload['corpus']['documents']), 3)
            self.assertTrue((self.directory / 'state-00000002.json').exists())

    def test_failed_pointer_replacement_keeps_old_head_and_preserves_uncommitted_files(self):
        with self.create() as store:
            before = (self.directory / 'current.json').read_bytes()
            payload = store.payload
            payload['scenario'] = 'stale'
            with patch.object(state_store.os, 'replace', side_effect=OSError('fictional failure')):
                with self.assertRaises(StateError):store.commit(payload)
            self.assertFalse(store.healthy)
            self.assertEqual((self.directory / 'current.json').read_bytes(), before)
            with self.assertRaises(StateError):store.ensure_available()
        with StateStore(self.directory) as store:
            self.assertEqual(store.payload['scenario'], 'fresh')
            store.commit(payload)
            self.assertEqual(store.generation, 3)
        self.assertTrue((self.directory / 'head-00000002.pending').exists())

    def test_failure_after_publication_is_unacknowledged_and_requires_reopen(self):
        with self.create() as store:
            payload = store.payload
            payload['scenario'] = 'stale'
            with patch.object(state_store.os, 'fsync', side_effect=[None, None, None, OSError('fictional failure')]):
                with self.assertRaises(StateError):store.commit(payload)
            with self.assertRaises(StateError):_ = store.payload
        with StateStore(self.directory) as store:
            self.assertEqual(store.generation, 2)
            self.assertEqual(store.payload['scenario'], 'stale')

    def test_history_limit_and_generation_conflict_refuse_writes(self):
        with self.create() as store:
            with patch.object(state_store, 'MAX_GENERATIONS', 1):
                with self.assertRaises(StateError):store.commit(store.payload)
        with StateStore(self.directory) as store:
            with self.assertRaises(StateError):store.commit(store.payload, expected=2)
        with StateStore(self.directory) as store:self.assertEqual(store.generation, 1)

    def test_future_schema_and_duplicate_head_are_refused(self):
        with self.create():pass
        head = self.directory / 'current.json'
        before = head.read_bytes()
        head.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ValueError):StateStore(self.directory)
        head.write_bytes(before)
        file = self.directory / 'state-00000001.json'
        envelope = json.loads(file.read_text())
        envelope['payload']['schema_version'] = 99
        envelope['sha256'] = hashlib.sha256(canonical(envelope['payload'])).hexdigest()
        raw = canonical(envelope)
        file.write_bytes(raw)
        head.write_bytes(canonical({'schema_version': 1, 'generation': 1, 'sha256': hashlib.sha256(raw).hexdigest()}))
        with self.assertRaises(ValueError):StateStore(self.directory)

    def test_empty_index_stays_empty_across_restart(self):
        with self.create() as store:
            payload = store.payload
            payload['corpus']['documents'] = []
            store.commit(payload)
        workspace = run.workspace_persistent(self.directory)
        try:self.assertEqual(workspace.index.search('lamp', 'owner')['results'], [])
        finally:workspace.close()

    def test_cli_fixed_errors_do_not_echo_private_inputs(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(run.main(['state', 'inspect', '--directory', str(self.parent / 'fictional-private-marker')]), 1)
        self.assertNotIn('fictional-private-marker', output.getvalue())
        self.assertNotIn(str(self.parent), output.getvalue())

    def test_disposable_rehearsal_needs_no_network_or_subprocess(self):
        with patch('socket.socket', side_effect=AssertionError('network')), \
             patch('subprocess.run', side_effect=AssertionError('subprocess')):
            self.assertEqual(rehearsal(run.seed_state)['result'], 'PASS')

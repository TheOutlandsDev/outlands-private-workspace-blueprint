"""Private, bounded synthetic generations. No sessions or real-data adapters."""
import copy
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat

from retrieval import Index
from runtime_io import private_report, unique_pairs, reject_constant

CHECKOUT = Path(__file__).resolve().parents[2]
MAX_PAYLOAD = 131_072
MAX_GENERATION_BYTES = MAX_PAYLOAD + 512
MAX_GENERATIONS = 64
MAX_ENTRIES = 130
CURRENT_SCHEMA = 2
SCENARIOS = {'fresh', 'stale', 'unavailable'}


class StateError(Exception):
    """A fixed failure boundary; never echo filesystem exceptions to HTTP/CLI."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def decode(data):
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique_pairs,
                      parse_constant=reject_constant)


def validate_payload(value):
    if not isinstance(value, dict) or type(value.get('schema_version')) is not int:
        raise ValueError('state schema')
    schema = value['schema_version']
    fields = {'schema_version', 'synthetic_fixture', 'scenario', 'corpus'}
    if schema == 2:
        fields.add('reset_count')
    if (schema not in {1, 2} or set(value) != fields
            or value['synthetic_fixture'] is not True
            or not isinstance(value['scenario'], str) or value['scenario'] not in SCENARIOS):
        raise ValueError('state contract')
    if schema == 2 and (type(value['reset_count']) is not int or not 0 <= value['reset_count'] <= 1_000_000):
        raise ValueError('reset bound')
    Index(value['corpus'])
    if len(canonical(value)) > MAX_PAYLOAD:
        raise ValueError('state bound')
    return value


def snapshot_payload(raw):
    envelope = decode(raw)
    if (not isinstance(envelope, dict) or set(envelope) != {'snapshot_schema', 'payload', 'sha256'}
            or type(envelope['snapshot_schema']) is not int or envelope['snapshot_schema'] != 1
            or not isinstance(envelope['sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', envelope['sha256'])):
        raise ValueError('snapshot contract')
    payload = validate_payload(envelope['payload'])
    if not hmac.compare_digest(hashlib.sha256(canonical(payload)).hexdigest(), envelope['sha256']):
        raise ValueError('snapshot checksum')
    return payload


def private_location(path, parent=False):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or path.is_relative_to(CHECKOUT):
        raise ValueError('private location')
    for ancestor in [path, *path.parents]:
        marker = ancestor / '.git'
        if marker.is_symlink() or (marker.exists() and not marker.is_dir()):
            raise ValueError('outside Git required')
        if marker.is_dir():
            # Empty permission-marker directories are not Git repositories.
            with os.scandir(marker) as metadata:
                if next(metadata, None) is not None:
                    raise ValueError('outside Git required')
        if ancestor != path and (ancestor / 'current.json').exists() and (ancestor / 'lock').exists():
            raise ValueError('nested state refused')
    selected = path.parent if parent else path
    info = selected.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('private directory required')
    return path


def valid_meta(info, limit):
    return (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
            and 0 <= info.st_size <= limit)


def read_fd(fd, limit):
    before = os.fstat(fd)
    if not valid_meta(before, limit):
        raise ValueError('private regular file required')
    data = os.read(fd, limit + 1)
    after = os.fstat(fd)
    if (len(data) != before.st_size or len(data) > limit
            or (after.st_size, after.st_mtime_ns, after.st_nlink)
            != (before.st_size, before.st_mtime_ns, 1)):
        raise ValueError('file changed')
    return data


class StateStore:
    def __init__(self, directory, _initial=None):
        self.directory = private_location(directory)
        self.dfd = self.lock_fd = None
        self.healthy = True
        self.generation = 0
        self.checksum = None
        try:
            self.dfd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self.lock_fd = os.open('lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.dfd)
            if not valid_meta(os.fstat(self.lock_fd), 0):
                raise ValueError('lock contract')
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            names, _numbers = self._entries()
            if _initial is not None:
                if names != {'lock'}:
                    raise ValueError('initial state not empty')
                self._publish(validate_payload(copy.deepcopy(_initial)))
            else:
                self.generation, self.checksum, self._payload = self._read_current()
        except BaseException:
            self.close()
            raise

    @classmethod
    def create(cls, directory, payload):
        payload = validate_payload(copy.deepcopy(payload))
        path = private_location(directory, parent=True)
        path.mkdir(mode=0o700)  # Never replace or initialize an existing directory.
        fd = os.open(path / 'lock', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        store = cls(path, _initial=payload)
        try:
            parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:os.fsync(parent_fd)
            finally:os.close(parent_fd)
        except BaseException:
            store.close()
            raise
        return store

    def close(self):
        for attribute in ['lock_fd', 'dfd']:
            fd = getattr(self, attribute, None)
            if fd is not None:
                os.close(fd)
                setattr(self, attribute, None)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def _entries(self):
        if self.dfd is None or not self.healthy:
            raise StateError('state unavailable')
        private_location(self.directory)
        root = self.directory.lstat()
        opened = os.fstat(self.dfd)
        if ((root.st_dev, root.st_ino) != (opened.st_dev, opened.st_ino)
                or root.st_uid != os.getuid() or stat.S_IMODE(root.st_mode) != 0o700):
            raise ValueError('state directory changed')
        lock = os.stat('lock', dir_fd=self.dfd, follow_symlinks=False)
        held = os.fstat(self.lock_fd)
        if (lock.st_dev, lock.st_ino) != (held.st_dev, held.st_ino):
            raise ValueError('lock changed')
        names, numbers = set(), []
        with os.scandir(self.dfd) as listing:
            for entry in listing:
                names.add(entry.name)
                if len(names) > MAX_ENTRIES:
                    raise ValueError('directory bound')
                generation = re.fullmatch(r'state-([0-9]{8})\.json', entry.name)
                pending = re.fullmatch(r'head-([0-9]{8})\.pending', entry.name)
                if entry.name not in {'lock', 'current.json'} and not generation and not pending:
                    raise ValueError('unexpected state entry')
                if generation or pending:
                    number = int((generation or pending).group(1))
                    if not 1 <= number <= 1_000_000:
                        raise ValueError('generation bound')
                    if generation:numbers.append(number)
                limit = MAX_GENERATION_BYTES if generation else 4096 if entry.name != 'lock' else 0
                if not valid_meta(os.stat(entry.name, dir_fd=self.dfd, follow_symlinks=False), limit):
                    raise ValueError('state file contract')
        if len(numbers) > MAX_GENERATIONS:
            raise ValueError('history bound')
        return names, numbers

    def _read(self, name, limit):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.dfd)
        try:
            return read_fd(fd, limit)
        finally:
            os.close(fd)

    def _read_current(self):
        self._entries()
        head = decode(self._read('current.json', 4096))
        if (not isinstance(head, dict) or set(head) != {'schema_version', 'generation', 'sha256'}
                or type(head['schema_version']) is not int or head['schema_version'] != 1
                or type(head['generation']) is not int or not 1 <= head['generation'] <= 1_000_000
                or not isinstance(head['sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', head['sha256'])):
            raise ValueError('head contract')
        raw = self._read(f'state-{head["generation"]:08d}.json', MAX_GENERATION_BYTES)
        if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), head['sha256']):
            raise ValueError('checksum mismatch')
        return head['generation'], head['sha256'], snapshot_payload(raw)

    @property
    def payload(self):
        self.ensure_available()
        return copy.deepcopy(self._payload)

    def ensure_available(self):
        if not self.healthy or self.dfd is None:
            raise StateError('state unavailable')

    def _write_new(self, name, raw):
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.dfd)
        try:
            remaining = memoryview(raw)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise OSError('incomplete write')
                remaining = remaining[written:]
            os.fsync(fd)
        finally:
            os.close(fd)

    def _publish(self, payload):
        _names, numbers = self._entries()
        if len(numbers) >= MAX_GENERATIONS:
            raise ValueError('history full')
        generation = max(numbers, default=0) + 1
        if generation > 1_000_000:
            raise ValueError('generation bound')
        raw = canonical({'snapshot_schema': 1, 'payload': payload,
                         'sha256': hashlib.sha256(canonical(payload)).hexdigest()})
        checksum = hashlib.sha256(raw).hexdigest()
        self._write_new(f'state-{generation:08d}.json', raw)
        os.fsync(self.dfd)
        pending = f'head-{generation:08d}.pending'
        self._write_new(pending, canonical({'schema_version': 1, 'generation': generation, 'sha256': checksum}))
        os.replace(pending, 'current.json', src_dir_fd=self.dfd, dst_dir_fd=self.dfd)
        os.fsync(self.dfd)
        self.generation, self.checksum, self._payload = generation, checksum, copy.deepcopy(payload)

    def commit(self, payload, expected=None):
        validate_payload(payload)
        try:
            self.ensure_available()
            generation, checksum, _current = self._read_current()
            if (generation != self.generation or checksum != self.checksum
                    or (expected is not None and (type(expected) is not int or expected != generation))):
                raise ValueError('state conflict')
            self._publish(copy.deepcopy(payload))
        except (OSError, ValueError):
            self.healthy = False
            raise StateError('state commit refused') from None

    def upgrade(self, expected):
        payload = self.payload
        if type(expected) is not int or expected != self.generation:
            raise ValueError('generation conflict')
        if payload['schema_version'] == CURRENT_SCHEMA:
            return False
        payload.update(schema_version=CURRENT_SCHEMA, reset_count=0)
        self.commit(payload, expected)
        return True

    def rollback(self, generation, expected):
        if type(generation) is not int or not 1 <= generation < self.generation:
            raise ValueError('rollback generation')
        payload = snapshot_payload(self._read(f'state-{generation:08d}.json', MAX_GENERATION_BYTES))
        self.commit(payload, expected)

    def backup(self, destination):
        destination = private_location(destination, parent=True)
        if destination.is_relative_to(self.directory):
            raise ValueError('backup outside state required')
        generation, checksum, payload = self._read_current()
        if generation != self.generation or checksum != self.checksum:
            raise StateError('state conflict')
        envelope = {'backup_schema': 1, 'synthetic_fixture': True, 'payload': payload,
                    'sha256': hashlib.sha256(canonical(payload)).hexdigest()}
        private_report(destination, envelope)
        fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)


def restore(source, directory):
    source = private_location(source, parent=True)
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        envelope = decode(read_fd(fd, MAX_PAYLOAD * 2))
    finally:
        os.close(fd)
    if (not isinstance(envelope, dict)
            or set(envelope) != {'backup_schema', 'synthetic_fixture', 'payload', 'sha256'}
            or type(envelope['backup_schema']) is not int or envelope['backup_schema'] != 1
            or envelope['synthetic_fixture'] is not True
            or not isinstance(envelope['sha256'], str)
            or not re.fullmatch(r'[a-f0-9]{64}', envelope['sha256'])):
        raise ValueError('backup contract')
    payload = validate_payload(envelope['payload'])
    if not hmac.compare_digest(hashlib.sha256(canonical(payload)).hexdigest(), envelope['sha256']):
        raise ValueError('backup checksum')
    return StateStore.create(directory, payload)

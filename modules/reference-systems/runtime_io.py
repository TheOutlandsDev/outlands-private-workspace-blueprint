"""Bounded input and private no-overwrite reports for Linux reference tools."""
import json
import os
from pathlib import Path
import re
import stat


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9-]{0,47}', value)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError('nonfinite number')


def load_json(path, limit=131_072):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise ValueError('input bound')
        data = os.read(fd, limit + 1)
        after = os.fstat(fd)
        if (len(data) != info.st_size or len(data) > limit
                or (after.st_size, after.st_mtime_ns) != (info.st_size, info.st_mtime_ns)):
            raise ValueError('input changed')
    finally:
        os.close(fd)
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique_pairs,
                      parse_constant=reject_constant)


def private_report(destination, value):
    path = Path(destination)
    parent = path.parent
    if not path.is_absolute() or parent.resolve() != parent:
        raise ValueError('private destination')
    dfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(dfd)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('private parent')
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=dfd)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(dfd)

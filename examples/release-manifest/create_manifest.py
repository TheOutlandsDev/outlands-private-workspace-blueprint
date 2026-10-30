#!/usr/bin/env python3
"""Build an exact-file manifest from an explicit allowlist and frozen export."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_ALLOWLIST_BYTES = 65_536
MAX_FILES = 128
MAX_ENTRIES = 256
MAX_FILE_BYTES = 2_000_000
MAX_TOTAL_BYTES = 8_000_000
SEGMENT = re.compile(r"[A-Za-z0-9._-]+\Z")
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW


class CreateError(Exception):
    """A fixed error code without input values."""


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CreateError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def reject_constant(_value):
    raise CreateError("ALLOWLIST_JSON")


def valid_path(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 240:
        raise CreateError("PATH")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or not SEGMENT.fullmatch(part)
           for part in parts):
        raise CreateError("PATH")
    return value


def read_allowlist(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise CreateError("SYMLINK")
    if not stat.S_ISREG(info.st_mode):
        raise CreateError("ALLOWLIST_TYPE")
    fd = os.open(path, FILE_FLAGS)
    try:
        current = os.fstat(fd)
        if (not stat.S_ISREG(current.st_mode) or
                (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino)):
            raise CreateError("CHANGED")
        if current.st_size > MAX_ALLOWLIST_BYTES:
            raise CreateError("ALLOWLIST_SIZE")
        data = bytearray()
        while len(data) <= MAX_ALLOWLIST_BYTES:
            chunk = os.read(fd, min(65_536, MAX_ALLOWLIST_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) > MAX_ALLOWLIST_BYTES:
            raise CreateError("ALLOWLIST_SIZE")
        if os.fstat(fd).st_size != len(data):
            raise CreateError("CHANGED")
    finally:
        os.close(fd)
    document = json.loads(bytes(data).decode("utf-8"),
                          object_pairs_hook=unique_pairs,
                          parse_constant=reject_constant)
    if (type(document) is not dict or set(document) != {"schema_version", "paths"}
            or type(document["schema_version"]) is not int
            or document["schema_version"] != 1):
        raise CreateError("ALLOWLIST_SHAPE")
    paths = document["paths"]
    if type(paths) is not list or not 1 <= len(paths) <= MAX_FILES:
        raise CreateError("FILE_COUNT")
    selected = [valid_path(value) for value in paths]
    if len(set(selected)) != len(selected):
        raise CreateError("DUPLICATE_PATH")
    if selected != sorted(selected):
        raise CreateError("ORDER")
    return set(selected)


def ensure_outside(root, candidate):
    real_root = root.resolve(strict=True)
    real_candidate = candidate.resolve(strict=False)
    if real_candidate == real_root or real_candidate.is_relative_to(real_root):
        raise CreateError("LOCATION")


def scan_export(root, selected):
    info = root.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise CreateError("SYMLINK")
    if not stat.S_ISDIR(info.st_mode):
        raise CreateError("ROOT_TYPE")
    found = {}
    total = 0
    entries_seen = 0

    def visit(directory_fd, prefix):
        nonlocal total, entries_seen
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                entries_seen += 1
                if entries_seen > MAX_ENTRIES:
                    raise CreateError("ENTRY_COUNT")
                name = f"{prefix}/{entry.name}" if prefix else entry.name
                valid_path(name)
                entry_info = os.stat(entry.name, dir_fd=directory_fd,
                                     follow_symlinks=False)
                if stat.S_ISLNK(entry_info.st_mode):
                    raise CreateError("SYMLINK")
                if stat.S_ISDIR(entry_info.st_mode):
                    child_fd = os.open(entry.name, DIR_FLAGS, dir_fd=directory_fd)
                    try:
                        current = os.fstat(child_fd)
                        if (current.st_dev, current.st_ino) != (entry_info.st_dev, entry_info.st_ino):
                            raise CreateError("CHANGED")
                        visit(child_fd, name)
                    finally:
                        os.close(child_fd)
                    continue
                if not stat.S_ISREG(entry_info.st_mode):
                    raise CreateError("FILE_TYPE")
                if name not in selected:
                    raise CreateError("EXTRA_FILE")
                if entry_info.st_nlink != 1:
                    raise CreateError("HARDLINK")
                size = entry_info.st_size
                if size > MAX_FILE_BYTES:
                    raise CreateError("FILE_SIZE")
                if total + size > MAX_TOTAL_BYTES:
                    raise CreateError("TOTAL_SIZE")
                file_fd = os.open(entry.name, FILE_FLAGS, dir_fd=directory_fd)
                try:
                    current = os.fstat(file_fd)
                    if (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1
                            or (current.st_dev, current.st_ino)
                            != (entry_info.st_dev, entry_info.st_ino)):
                        raise CreateError("CHANGED")
                    digest = hashlib.sha256()
                    count = 0
                    while True:
                        chunk = os.read(file_fd, min(65_536, size - count + 1))
                        if not chunk:
                            break
                        count += len(chunk)
                        if count > size:
                            raise CreateError("CHANGED")
                        digest.update(chunk)
                    if count != size or os.fstat(file_fd).st_size != count:
                        raise CreateError("CHANGED")
                finally:
                    os.close(file_fd)
                found[name] = {"path": name, "bytes": size,
                               "sha256": digest.hexdigest()}
                total += size

    root_fd = os.open(root, DIR_FLAGS)
    try:
        current = os.fstat(root_fd)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise CreateError("CHANGED")
        visit(root_fd, "")
    finally:
        os.close(root_fd)
    if set(found) != selected:
        raise CreateError("MISSING_FILE")
    return {"schema_version": 1,
            "files": [found[name] for name in sorted(found)]}, total


def create(allowlist_path, export_root, output_path):
    allowlist = Path(allowlist_path)
    root = Path(export_root)
    output = Path(output_path)
    ensure_outside(root, allowlist)
    ensure_outside(root, output)
    selected = read_allowlist(allowlist)
    document, total = scan_export(root, selected)
    data = (json.dumps(document, indent=2) + "\n").encode("utf-8")
    try:
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600)
    except FileExistsError:
        raise CreateError("OUTPUT_EXISTS") from None
    try:
        with os.fdopen(fd, "wb") as destination:
            destination.write(data)
            destination.flush()
            os.fsync(destination.fileno())
    except OSError:
        raise CreateError("OUTPUT_WRITE") from None
    return {"result": "CREATED", "files_checked": len(selected),
            "bytes_checked": total, "privacy_cleared": False,
            "rights_cleared": False}


def main(argv):
    if len(argv) != 4:
        print("ERROR: USAGE")
        return 2
    try:
        result = create(argv[1], argv[2], argv[3])
    except CreateError as error:
        print(f"ERROR: {error}")
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RuntimeError):
        print("ERROR: INPUT")
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

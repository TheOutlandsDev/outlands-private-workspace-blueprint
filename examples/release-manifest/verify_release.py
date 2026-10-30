#!/usr/bin/env python3
"""Verify a small, frozen export against an external exact-file manifest."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_MANIFEST_BYTES = 65_536
MAX_FILES = 128
MAX_ENTRIES = 256
MAX_FILE_BYTES = 2_000_000
MAX_TOTAL_BYTES = 8_000_000
SEGMENT = re.compile(r"[A-Za-z0-9._-]+\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW


class ReleaseError(Exception):
    """A fixed code that can be printed without disclosing input values."""


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def reject_constant(_value):
    raise ReleaseError("MANIFEST_JSON")


def validate_path(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 240:
        raise ReleaseError("PATH")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or not SEGMENT.fullmatch(part)
           for part in parts):
        raise ReleaseError("PATH")
    return value


def read_manifest(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise ReleaseError("SYMLINK")
    if not stat.S_ISREG(info.st_mode):
        raise ReleaseError("MANIFEST_TYPE")
    fd = os.open(path, FILE_FLAGS)
    try:
        current = os.fstat(fd)
        if (not stat.S_ISREG(current.st_mode) or
                (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino)):
            raise ReleaseError("CHANGED")
        if current.st_size > MAX_MANIFEST_BYTES:
            raise ReleaseError("MANIFEST_SIZE")
        data = bytearray()
        while len(data) <= MAX_MANIFEST_BYTES:
            chunk = os.read(fd, min(65_536, MAX_MANIFEST_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) > MAX_MANIFEST_BYTES:
            raise ReleaseError("MANIFEST_SIZE")
        if os.fstat(fd).st_size != len(data):
            raise ReleaseError("CHANGED")
    finally:
        os.close(fd)
    document = json.loads(bytes(data).decode("utf-8"),
                          object_pairs_hook=unique_pairs,
                          parse_constant=reject_constant)
    if (type(document) is not dict or set(document) != {"schema_version", "files"}
            or type(document["schema_version"]) is not int
            or document["schema_version"] != 1):
        raise ReleaseError("MANIFEST_SHAPE")
    files = document["files"]
    if type(files) is not list or not 1 <= len(files) <= MAX_FILES:
        raise ReleaseError("FILE_COUNT")
    expected = {}
    total = 0
    for item in files:
        if type(item) is not dict or set(item) != {"path", "bytes", "sha256"}:
            raise ReleaseError("FILE_SHAPE")
        name = validate_path(item["path"])
        if name in expected:
            raise ReleaseError("DUPLICATE_PATH")
        if type(item["bytes"]) is not int or not 0 <= item["bytes"] <= MAX_FILE_BYTES:
            raise ReleaseError("FILE_SIZE")
        if not isinstance(item["sha256"], str) or not SHA256.fullmatch(item["sha256"]):
            raise ReleaseError("HASH_SHAPE")
        expected[name] = item
        total += item["bytes"]
    if list(expected) != sorted(expected):
        raise ReleaseError("ORDER")
    if total > MAX_TOTAL_BYTES:
        raise ReleaseError("TOTAL_SIZE")
    return expected


def verify(manifest_path, export_root):
    expected = read_manifest(Path(manifest_path))
    root = Path(export_root)
    info = root.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise ReleaseError("SYMLINK")
    if not stat.S_ISDIR(info.st_mode):
        raise ReleaseError("ROOT_TYPE")

    seen = set()
    total = 0
    entries_seen = 0

    def visit(directory_fd, prefix):
        nonlocal total, entries_seen
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                entries_seen += 1
                if entries_seen > MAX_ENTRIES:
                    raise ReleaseError("ENTRY_COUNT")
                name = f"{prefix}/{entry.name}" if prefix else entry.name
                validate_path(name)
                entry_info = os.stat(entry.name, dir_fd=directory_fd,
                                     follow_symlinks=False)
                if stat.S_ISLNK(entry_info.st_mode):
                    raise ReleaseError("SYMLINK")
                if stat.S_ISDIR(entry_info.st_mode):
                    child_fd = os.open(entry.name, DIR_FLAGS, dir_fd=directory_fd)
                    try:
                        current = os.fstat(child_fd)
                        if (current.st_dev, current.st_ino) != (entry_info.st_dev, entry_info.st_ino):
                            raise ReleaseError("CHANGED")
                        visit(child_fd, name)
                    finally:
                        os.close(child_fd)
                    continue
                if not stat.S_ISREG(entry_info.st_mode):
                    raise ReleaseError("FILE_TYPE")
                if name not in expected:
                    raise ReleaseError("EXTRA_FILE")
                if entry_info.st_nlink != 1:
                    raise ReleaseError("HARDLINK")
                item = expected[name]
                if entry_info.st_size != item["bytes"]:
                    raise ReleaseError("SIZE_MISMATCH")
                file_fd = os.open(entry.name, FILE_FLAGS, dir_fd=directory_fd)
                try:
                    current = os.fstat(file_fd)
                    if (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1
                            or (current.st_dev, current.st_ino)
                            != (entry_info.st_dev, entry_info.st_ino)):
                        raise ReleaseError("CHANGED")
                    digest = hashlib.sha256()
                    count = 0
                    while True:
                        chunk = os.read(file_fd, min(65_536, item["bytes"] - count + 1))
                        if not chunk:
                            break
                        count += len(chunk)
                        if count > item["bytes"]:
                            raise ReleaseError("SIZE_MISMATCH")
                        digest.update(chunk)
                    if count != item["bytes"] or os.fstat(file_fd).st_size != count:
                        raise ReleaseError("SIZE_MISMATCH")
                    if digest.hexdigest() != item["sha256"]:
                        raise ReleaseError("HASH_MISMATCH")
                finally:
                    os.close(file_fd)
                seen.add(name)
                total += count

    root_fd = os.open(root, DIR_FLAGS)
    try:
        current = os.fstat(root_fd)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise ReleaseError("CHANGED")
        visit(root_fd, "")
    finally:
        os.close(root_fd)
    if seen != set(expected):
        raise ReleaseError("MISSING_FILE")
    return {"result": "PASS", "files_checked": len(seen),
            "bytes_checked": total, "privacy_cleared": False,
            "rights_cleared": False}


def main(argv):
    if len(argv) != 3:
        print("ERROR: USAGE")
        return 2
    try:
        summary = verify(argv[1], argv[2])
    except ReleaseError as error:
        print(f"ERROR: {error}")
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        print("ERROR: INPUT")
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""Disposable runner volume archive helper. No network or backup provider."""

import argparse
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile


MARKER = "_outlands_disposable_restore_marker.txt"
MARKER_TEXT = "fictional model-volume restore marker\n"
MAX_MEMBERS = 20_000
MAX_BYTES = 4_000_000_000


def mark(volume: Path) -> None:
    with (volume / MARKER).open("x", encoding="utf-8") as output:
        output.write(MARKER_TEXT)


def verify_marker(volume: Path) -> None:
    if (volume / MARKER).read_text(encoding="utf-8") != MARKER_TEXT:
        raise ValueError("fictional model-volume marker mismatch")


def backup(volume: Path, archive: Path) -> None:
    if not volume.is_dir() or archive.exists() or archive.is_symlink():
        raise ValueError("backup input or output boundary")
    members = sorted(volume.rglob("*"))
    if not members or len(members) > MAX_MEMBERS:
        raise ValueError("backup member boundary")
    total = 0
    for item in members:
        if item.is_symlink():
            if (PurePosixPath(os.readlink(item)).is_absolute()
                    or not item.resolve().is_relative_to(volume.resolve())):
                raise ValueError("unsafe source symlink")
        elif not (item.is_file() or item.is_dir()):
            raise ValueError("unsupported volume entry")
        if item.is_file() and not item.is_symlink():
            total += item.stat().st_size
    if total > MAX_BYTES:
        raise ValueError("backup size boundary")
    with archive.open("xb") as output, tarfile.open(fileobj=output, mode="w:gz") as tar:
        for item in members:
            tar.add(item, arcname=item.relative_to(volume).as_posix(), recursive=False)


def restore(volume: Path, archive: Path) -> None:
    if not volume.is_dir() or any(volume.iterdir()) or not archive.is_file() or archive.is_symlink():
        raise ValueError("restore input or output boundary")
    count = 0
    total = 0
    directories = []
    symlinks = []
    with tarfile.open(archive, mode="r:gz") as tar:
        for member in tar:
            count += 1
            total += member.size
            path = PurePosixPath(member.name)
            if (count > MAX_MEMBERS or total > MAX_BYTES or path.is_absolute()
                    or not path.parts or any(part in (".", "..") for part in path.parts)
                    or not (member.isdir() or member.isfile() or member.issym())):
                raise ValueError("unsafe archive member")
            target = volume.joinpath(*path.parts)
            if not target.resolve().is_relative_to(volume.resolve()):
                raise ValueError("archive path escape")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                directories.append((target, member.mode & 0o777))
            elif member.issym():
                link = PurePosixPath(member.linkname)
                if (link.is_absolute()
                        or not (target.parent / member.linkname).resolve().is_relative_to(volume.resolve())):
                    raise ValueError("unsafe archive symlink")
                symlinks.append((target, member.linkname))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tar.extractfile(member)
                if source is None:
                    raise ValueError("archive file missing")
                with source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                os.chmod(target, member.mode & 0o666)
    if count == 0:
        raise ValueError("empty archive")
    for target, link in symlinks:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(link)
    for target, mode in sorted(directories, key=lambda pair: len(pair[0].parts), reverse=True):
        os.chmod(target, mode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("mark", "backup", "restore", "verify-marker"))
    parser.add_argument("kind", choices=("ollama", "webui"))
    args = parser.parse_args()
    if os.environ.get("OUTLANDS_DISPOSABLE_RESTORE") != "1":
        print("REVIEW: disposable-runner marker required", file=sys.stderr)
        return 2
    volume = Path("/volume")
    archive = Path("/archive") / (args.kind + ".tar.gz")
    try:
        if args.action == "mark" and args.kind == "ollama":
            mark(volume)
        elif args.action == "verify-marker" and args.kind == "ollama":
            verify_marker(volume)
        elif args.action == "backup":
            backup(volume, archive)
        elif args.action == "restore":
            restore(volume, archive)
        else:
            raise ValueError("marker action requires ollama kind")
    except ValueError as error:
        # These fixed labels contain no source paths, identities, or archive content.
        print("REVIEW: " + str(error), file=sys.stderr)
        return 1
    except (OSError, tarfile.TarError) as error:
        print(f"REVIEW: {type(error).__name__}; inspect disposable runner privately", file=sys.stderr)
        return 1
    print("PASS disposable volume " + args.action + ": " + args.kind)
    return 0


if __name__ == "__main__":
    sys.exit(main())

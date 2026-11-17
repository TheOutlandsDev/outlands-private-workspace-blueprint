"""Explicit-root Linux source inventory. Never emit filenames or file contents."""
from datetime import datetime, timezone
import os
from pathlib import Path
import stat

from runtime_io import private_report

EXCLUDED_DIRS = {'.git', '.secrets', '.venv', '__pycache__', 'node_modules',
                 'vendor', 'build', 'dist', 'generated'}
CODE = {'.py', '.js', '.ts', '.rs', '.sh', '.css', '.html'}
CONFIG = {'.json', '.toml', '.yaml', '.yml'}
PROSE = {'.md', '.txt'}
MAX_ENTRIES, MAX_FILES, MAX_FILE, MAX_BYTES, MAX_DEPTH = 512, 128, 65536, 1048576, 16


def scan(root, synthetic=False):
    path = Path(root)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('explicit absolute root')
    root_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(root_fd)
        if not synthetic and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError('private root required')
        result = {kind: {'files': 0, 'lines': 0, 'nonblank_lines': 0}
                  for kind in ['code', 'configuration', 'prose']}
        excluded_files = excluded_dirs = entries = file_count = total = 0

        def visit(dfd, depth):
            nonlocal excluded_files, excluded_dirs, entries, file_count, total
            if depth > MAX_DEPTH:
                raise ValueError('depth bound')
            before = os.fstat(dfd)
            names = []
            with os.scandir(dfd) as listing:
                for entry in listing:
                    entries += 1
                    if entries > MAX_ENTRIES:
                        raise ValueError('entry bound')
                    names.append(entry.name)
            for name in sorted(names):
                meta = os.stat(name, dir_fd=dfd, follow_symlinks=False)
                if stat.S_ISDIR(meta.st_mode):
                    if name in EXCLUDED_DIRS:
                        excluded_dirs += 1
                        continue
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dfd)
                    try:
                        opened = os.fstat(child)
                        if ((opened.st_dev, opened.st_ino) != (meta.st_dev, meta.st_ino)
                                or opened.st_dev != info.st_dev):
                            raise ValueError('directory changed or mount')
                        visit(child, depth + 1)
                    finally:
                        os.close(child)
                    continue
                if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1:
                    raise ValueError('link or special file')
                suffix = Path(name).suffix.lower()
                category = ('code' if suffix in CODE else 'configuration' if suffix in CONFIG
                            else 'prose' if suffix in PROSE else None)
                if category is None or name.startswith('.'):
                    excluded_files += 1
                    continue
                file_count += 1
                total += meta.st_size
                if file_count > MAX_FILES or meta.st_size > MAX_FILE or total > MAX_BYTES:
                    raise ValueError('file bound')
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
                try:
                    opened = os.fstat(fd)
                    if ((opened.st_dev, opened.st_ino, opened.st_mtime_ns, opened.st_size)
                            != (meta.st_dev, meta.st_ino, meta.st_mtime_ns, meta.st_size)
                            or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1):
                        raise ValueError('file changed')
                    data = os.read(fd, MAX_FILE + 1)
                    after = os.fstat(fd)
                    if (len(data) != meta.st_size
                            or (after.st_mtime_ns, after.st_size, after.st_nlink)
                            != (opened.st_mtime_ns, opened.st_size, 1)):
                        raise ValueError('file changed')
                finally:
                    os.close(fd)
                if b'\0' in data:
                    raise ValueError('binary source')
                lines = data.decode('utf-8').splitlines()
                result[category]['files'] += 1
                result[category]['lines'] += len(lines)
                result[category]['nonblank_lines'] += sum(bool(line.strip()) for line in lines)
            if os.fstat(dfd).st_mtime_ns != before.st_mtime_ns:
                raise ValueError('directory changed')

        visit(root_fd, 0)
        return {'schema_version': 1, 'synthetic_fixture': synthetic,
                'observed_at': '2026-01-01T00:00:00Z' if synthetic else
                datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'coverage': 'PARTIAL_BY_POLICY', 'counts': result,
                'excluded_files': excluded_files, 'excluded_directories': excluded_dirs,
                'authorship_established': False}
    finally:
        os.close(root_fd)


def private_scan(root, destination):
    root_path = Path(root)
    if Path(destination).resolve().is_relative_to(root_path.resolve()):
        raise ValueError('report outside source root')
    report = scan(root_path)
    private_report(destination, report)
    return {'result': 'PASS', 'report_written': True, 'synthetic_fixture': False}

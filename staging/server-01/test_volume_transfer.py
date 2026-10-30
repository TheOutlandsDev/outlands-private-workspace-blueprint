"""Offline tests for fictional, local-only volume archive behavior."""

from pathlib import Path
import io
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from volume_transfer import backup, mark, restore, verify_marker


class VolumeTransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.source.mkdir()
        self.target.mkdir()
        self.archive = self.root / "fixture.tar.gz"

    def test_fictional_archive_restores_into_empty_volume(self):
        (self.source / "nested").mkdir()
        (self.source / "nested" / "state.txt").write_text("fictional state\n")
        mark(self.source)
        backup(self.source, self.archive)
        restore(self.target, self.archive)
        verify_marker(self.target)
        self.assertEqual((self.target / "nested" / "state.txt").read_text(),
                         "fictional state\n")

    def test_refuses_overwrite_and_nonempty_target(self):
        (self.source / "state.txt").write_text("fictional\n")
        backup(self.source, self.archive)
        with self.assertRaisesRegex(ValueError, "backup input"):
            backup(self.source, self.archive)
        (self.target / "existing.txt").write_text("preserve\n")
        with self.assertRaisesRegex(ValueError, "restore input"):
            restore(self.target, self.archive)
        self.assertEqual((self.target / "existing.txt").read_text(), "preserve\n")

    def test_rejects_volume_over_configured_size_limit(self):
        (self.source / "state.txt").write_text("fictional\n")
        with patch("volume_transfer.MAX_BYTES", 4):
            with self.assertRaisesRegex(ValueError, "backup size boundary"):
                backup(self.source, self.archive)
        self.assertFalse(self.archive.exists())

    def test_rejects_parent_traversal_member(self):
        with tarfile.open(self.archive, "w:gz") as archive:
            payload = b"synthetic\n"
            entry = tarfile.TarInfo("../escape.txt")
            entry.size = len(payload)
            archive.addfile(entry, io.BytesIO(payload))
        with self.assertRaisesRegex(ValueError, "unsafe archive"):
            restore(self.target, self.archive)
        self.assertFalse((self.root / "escape.txt").exists())

    def test_internal_relative_symlink_is_preserved(self):
        (self.source / "blobs").mkdir()
        (self.source / "snapshots").mkdir()
        (self.source / "blobs" / "state.txt").write_text("fictional\n")
        (self.source / "snapshots" / "link").symlink_to("../blobs/state.txt")
        backup(self.source, self.archive)
        restore(self.target, self.archive)
        self.assertEqual((self.target / "snapshots" / "link").read_text(), "fictional\n")
        self.assertTrue((self.target / "snapshots" / "link").is_symlink())

    def test_rejects_escaping_symlink_in_source(self):
        (self.source / "state.txt").write_text("fictional\n")
        (self.source / "link").symlink_to("../outside.txt")
        with self.assertRaisesRegex(ValueError, "unsafe source symlink"):
            backup(self.source, self.archive)
        self.assertFalse(self.archive.exists())

    def test_rejects_escaping_symlink_in_archive(self):
        with tarfile.open(self.archive, "w:gz") as archive:
            entry = tarfile.TarInfo("link")
            entry.type = tarfile.SYMTYPE
            entry.linkname = "../outside.txt"
            archive.addfile(entry)
        with self.assertRaisesRegex(ValueError, "unsafe archive symlink"):
            restore(self.target, self.archive)
        self.assertFalse((self.target / "link").exists())


if __name__ == "__main__":
    unittest.main()

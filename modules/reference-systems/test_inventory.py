import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import inventory
from runtime_io import load_json, private_report


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir(mode=0o700)
        (self.source / 'main.py').write_text('x = 1\n\n# fictional\n')

    def test_counts_prose_config_and_policy_exclusions_separately(self):
        (self.source / 'guide.md').write_text('fictional prose\n')
        (self.source / 'settings.toml').write_text('enabled = false\n')
        (self.source / 'unknown.bin').write_bytes(b'\0')
        (self.source / 'vendor').mkdir()
        (self.source / 'vendor/ignored.py').write_text('not counted\n')
        report = inventory.scan(self.source)
        self.assertEqual(report['counts']['code'], {'files': 1, 'lines': 3, 'nonblank_lines': 2})
        self.assertEqual(report['counts']['prose']['lines'], 1)
        self.assertEqual(report['counts']['configuration']['files'], 1)
        self.assertEqual(report['excluded_files'], 1)
        self.assertEqual(report['excluded_directories'], 1)
        self.assertEqual(report['coverage'], 'PARTIAL_BY_POLICY')
        self.assertNotIn('main.py', json.dumps(report))
        self.assertNotIn(str(self.source), json.dumps(report))

    def test_symlink_hardlink_and_fifo_are_refused(self):
        for kind in ['symlink', 'hardlink', 'fifo']:
            target = self.source / 'other.py'
            if kind == 'symlink':target.symlink_to(self.source / 'main.py')
            elif kind == 'hardlink':os.link(self.source / 'main.py', target)
            else:os.mkfifo(target)
            try:
                with self.assertRaises(ValueError):inventory.scan(self.source)
            finally:target.unlink()

    def test_symlink_directory_and_root_are_refused(self):
        link = self.root / 'linked'
        link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):inventory.scan(link)
        (self.source / 'sub').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):inventory.scan(self.source)

    def test_binary_size_count_and_entry_bounds(self):
        (self.source / 'main.py').write_bytes(b'\0')
        with self.assertRaises(ValueError):inventory.scan(self.source)
        (self.source / 'main.py').write_text('fictional\n')
        for key in ['MAX_FILE', 'MAX_BYTES', 'MAX_FILES', 'MAX_ENTRIES']:
            with patch.object(inventory, key, 0):
                with self.assertRaises(ValueError):inventory.scan(self.source)

    def test_private_report_is_no_overwrite_and_has_no_paths(self):
        output = self.root / 'report.json'
        inventory.private_scan(self.source, output)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(str(self.source), output.read_text())
        with self.assertRaises(FileExistsError):inventory.private_scan(self.source, output)
        with self.assertRaises(ValueError):inventory.private_scan(self.source, self.source / 'report.json')

    def test_public_root_or_report_parent_is_refused(self):
        self.source.chmod(0o755)
        with self.assertRaises(ValueError):inventory.scan(self.source)
        self.source.chmod(0o700)
        public = self.root / 'public'
        public.mkdir(mode=0o755)
        with self.assertRaises(ValueError):private_report(public / 'report.json', {})

    def test_changed_source_and_depth_bound_fail_without_report(self):
        original_read = os.read

        def change_after_read(fd, size):
            data = original_read(fd, size)
            (self.source / 'main.py').write_text('changed fictional source and size\n')
            return data

        with patch.object(inventory.os, 'read', side_effect=change_after_read):
            with self.assertRaises(ValueError):
                inventory.private_scan(self.source, self.root / 'failed.json')
        self.assertFalse((self.root / 'failed.json').exists())
        (self.source / 'nested').mkdir()
        with patch.object(inventory, 'MAX_DEPTH', 0):
            with self.assertRaises(ValueError):inventory.scan(self.source)

    def test_json_duplicate_nonfinite_symlink_and_size_refusal(self):
        file = self.root / 'input.json'
        for text in ['{"a":1,"a":2}', '{"a":NaN}']:
            file.write_text(text)
            with self.assertRaises(ValueError):load_json(file)
        file.write_text('{}')
        with self.assertRaises(ValueError):load_json(file, limit=1)
        link = self.root / 'input-link.json'
        link.symlink_to(file)
        with self.assertRaises(OSError):load_json(link)

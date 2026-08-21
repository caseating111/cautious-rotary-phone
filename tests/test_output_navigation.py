from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from tools.run_existing_pillow_from_config import (
    child_directories,
    cleanup_empty_new_directories,
    directory_has_content,
    newest_new_directory,
)


class OutputNavigationTests(unittest.TestCase):
    def test_detects_only_newly_created_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "old").mkdir()
            before = child_directories(root)
            time.sleep(0.001)
            created = root / "new"
            created.mkdir()
            after = child_directories(root)
            self.assertEqual(newest_new_directory(before, after), created.resolve())

    def test_returns_none_when_no_directory_was_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "old").mkdir()
            directories = child_directories(root)
            self.assertIsNone(newest_new_directory(directories, directories))

    def test_output_content_check_rejects_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "output"
            output.mkdir()
            self.assertFalse(directory_has_content(output))
            (output / "matrix.png").write_bytes(b"derived")
            self.assertTrue(directory_has_content(output))

    def test_failed_output_cleanup_removes_only_new_empty_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = root / "old"
            old.mkdir()
            before = child_directories(root)

            empty = root / "empty-new"
            nonempty = root / "partial-new"
            empty.mkdir()
            nonempty.mkdir()
            (nonempty / "partial.png").write_bytes(b"partial")
            after = child_directories(root)

            removed, retained = cleanup_empty_new_directories(before, after)
            self.assertEqual(removed, [empty.resolve()])
            self.assertEqual(retained, [nonempty.resolve()])
            self.assertFalse(empty.exists())
            self.assertTrue((nonempty / "partial.png").is_file())
            self.assertTrue(old.is_dir())


if __name__ == "__main__":
    unittest.main()

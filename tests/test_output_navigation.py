from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from tools.run_existing_pillow_from_config import child_directories, newest_new_directory


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


if __name__ == "__main__":
    unittest.main()

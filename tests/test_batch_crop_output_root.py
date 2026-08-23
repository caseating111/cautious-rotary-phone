from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.four_point_batch import ensure_crop_output_root


class BatchCropOutputRootTests(unittest.TestCase):
    def test_creates_nested_output_root_and_leaves_no_probe_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "derived" / "crops"
            self.assertFalse(root.exists())

            result = ensure_crop_output_root({"crop_output": str(root)})

            self.assertEqual(result, root)
            self.assertTrue(root.is_dir())
            self.assertEqual(list(root.iterdir()), [])

    def test_rejects_existing_file_as_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "crops"
            root.write_text("not a directory", encoding="utf-8")

            with self.assertRaises(SystemExit) as caught:
                ensure_crop_output_root({"crop_output": str(root)})

            self.assertIn("Could not create crop output folder", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

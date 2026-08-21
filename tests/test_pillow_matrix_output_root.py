from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.run_existing_pillow_from_config import ensure_matrix_output_root


class PillowMatrixOutputRootTests(unittest.TestCase):
    def test_creates_nested_matrix_root_and_leaves_no_probe_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "derived" / "matrices"
            self.assertFalse(root.exists())

            result = ensure_matrix_output_root({"matrix_output": str(root)})

            self.assertEqual(result, root)
            self.assertTrue(root.is_dir())
            self.assertEqual(list(root.iterdir()), [])

    def test_rejects_existing_file_as_matrix_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "matrices"
            root.write_text("not a directory", encoding="utf-8")

            with self.assertRaises(SystemExit) as caught:
                ensure_matrix_output_root({"matrix_output": str(root)})

            self.assertIn("Could not create matrix output folder", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

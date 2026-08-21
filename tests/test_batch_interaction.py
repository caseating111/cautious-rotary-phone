from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_full_column_batch_from_config as batch_adapter


class BatchInteractionTests(unittest.TestCase):
    def test_composed_batch_keeps_plate_identity_without_extra_modal(self) -> None:
        config = {
            "grid_csv": "C:/project/grid.csv",
            "images_csv": "C:/project/images.csv",
            "image_root": "C:/project/images",
            "crop_output": "C:/project/crops",
            "alignment_tolerance": 0.08,
            "crop_width": 130,
            "crop_height": 546,
        }
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "batch.ijm"
            pending = Path(temp) / "pending_images.csv"
            with patch.object(batch_adapter, "CONFIGURED_MACRO", output), patch.object(
                batch_adapter, "PENDING_IMAGES_CSV", pending
            ):
                built = batch_adapter.build_macro(config)

            text = built.read_text(encoding="utf-8")
            self.assertIn("showStatus(", text)
            self.assertIn('runMacro(', text)
            self.assertIn('"context=" + experiment + "/" + setName + "/" + typeName', text)
            self.assertNotIn('"Next plate"', text)
            self.assertNotIn("showMessage(\n            \"Next plate\"", text)


if __name__ == "__main__":
    unittest.main()

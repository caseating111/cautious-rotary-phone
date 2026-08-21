from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_full_column_batch_from_config as batch_adapter


class FullColumnGridWidthContractTests(unittest.TestCase):
    def config(self) -> dict:
        return {
            "grid_csv": "C:/project/grid.csv",
            "images_csv": "C:/project/images.csv",
            "image_root": "C:/project/images",
            "crop_output": "C:/project/crops",
            "alignment_tolerance": 0.08,
            "crop_width": 130,
            "crop_height": 546,
        }

    def test_composed_route_neutralizes_only_legacy_10_12_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "full.ijm"
            pending = root / "pending.csv"
            state = root / "state.txt"
            with patch.object(batch_adapter, "CONFIGURED_MACRO", output), patch.object(
                batch_adapter, "PENDING_IMAGES_CSV", pending
            ), patch.object(batch_adapter, "LEGACY_STATE_FILE", state):
                built = batch_adapter.build_macro(self.config())

            text = built.read_text(encoding="utf-8")
            self.assertNotIn("gridCols != 10 && gridCols != 12", text)
            self.assertIn("if (gridCols < 2) {", text)
            self.assertIn("FULL-COLUMN COMPOSED ROUTE", text)

    def test_preserved_four_point_route_keeps_original_10_12_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "legacy.ijm"
            pending = root / "pending.csv"
            state = root / "state.txt"
            with patch.object(batch_adapter, "CONFIGURED_LEGACY_MACRO", output), patch.object(
                batch_adapter, "PENDING_IMAGES_CSV", pending
            ), patch.object(batch_adapter, "LEGACY_STATE_FILE", state):
                built = batch_adapter.build_legacy_macro(self.config())

            text = built.read_text(encoding="utf-8")
            self.assertIn("gridCols != 10 && gridCols != 12", text)
            self.assertNotIn("FULL-COLUMN COMPOSED ROUTE", text)


if __name__ == "__main__":
    unittest.main()

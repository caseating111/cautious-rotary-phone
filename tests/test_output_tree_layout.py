from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_existing_pillow_from_config as pillow_adapter


class OutputTreeLayoutTests(unittest.TestCase):
    def test_matrix_output_cannot_live_inside_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "images"
            crops = root / "crops"

            with self.assertRaises(SystemExit) as caught:
                pillow_adapter.validate_output_layout(
                    crops,
                    source / "generated-matrices",
                    image_root=source,
                )
            self.assertIn("outside image_root", str(caught.exception))

            pillow_adapter.validate_output_layout(
                crops,
                root / "matrices",
                image_root=source,
            )

    def test_pillow_config_reports_malformed_json_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "config.json"
            config_path.write_text("{bad json", encoding="utf-8")

            with patch.object(pillow_adapter, "CONFIG_FILE", config_path):
                with self.assertRaises(SystemExit) as caught:
                    pillow_adapter.load_config()

            self.assertIn("Could not read config.json", str(caught.exception))

    def test_pillow_config_applies_source_tree_layout_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "images"
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "image_root": str(source),
                        "crop_output": str(root / "crops"),
                        "matrix_output": str(source / "matrices"),
                        "grid_csv": str(root / "grid.csv"),
                        "images_csv": str(root / "images.csv"),
                        "condition_order_csv": str(root / "condition_order.csv"),
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(pillow_adapter, "CONFIG_FILE", config_path):
                with self.assertRaises(SystemExit) as caught:
                    pillow_adapter.load_config()

            self.assertIn("outside image_root", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

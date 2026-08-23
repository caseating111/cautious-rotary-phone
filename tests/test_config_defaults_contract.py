from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import preflight_batch
from tools import run_existing_pillow_from_config as pillow_adapter
from tools import run_four_point_batch_from_config as batch_adapter
from tools import workflow_controller


class ConfigDefaultsContractTests(unittest.TestCase):
    def test_crop_defaults_stay_consistent_across_handoffs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "image_root": str(root / "images"),
                        "crop_output": str(root / "crops"),
                        "matrix_output": str(root / "matrices"),
                        "grid_csv": str(root / "grid.csv"),
                        "images_csv": str(root / "images.csv"),
                        "condition_order_csv": str(root / "condition_order.csv"),
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(batch_adapter, "CONFIG_FILE", config_path):
                batch = batch_adapter.load_config(require_fiji=False)
            preflight = preflight_batch.load_config(config_path)
            with patch.object(pillow_adapter, "CONFIG_FILE", config_path):
                pillow = pillow_adapter.load_config()
            with patch.object(workflow_controller, "CONFIG_FILE", config_path):
                controller = workflow_controller.load_config()

            self.assertEqual((batch["crop_width"], batch["crop_height"]), (130, 546))
            self.assertEqual((preflight["crop_width"], preflight["crop_height"]), (130, 546))
            self.assertEqual((pillow["crop_width"], pillow["crop_height"]), (130, 546))
            self.assertEqual((controller["crop_width"], controller["crop_height"]), ("130", "546"))


if __name__ == "__main__":
    unittest.main()

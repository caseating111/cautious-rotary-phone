from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import four_point_batch as batch_adapter


class FourPointPathRuleTests(unittest.TestCase):
    def test_four_point_config_accepts_paths_without_macro_argument_delimiter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "image_root": str(root / "images"),
                        "crop_output": str(root / "crop;output"),
                        "grid_csv": str(root / "grid;metadata.csv"),
                        "images_csv": str(root / "images.csv"),
                        "condition_order_csv": str(root / "condition_order.csv"),
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(batch_adapter, "CONFIG_FILE", config_path):
                loaded = batch_adapter.load_config(require_fiji=False)

            self.assertEqual(loaded["crop_output"], str(root / "crop;output"))
            self.assertEqual(loaded["grid_csv"], str(root / "grid;metadata.csv"))

    def test_four_point_preflight_uses_non_composed_path_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pending = root / "pending.csv"
            pending.write_text(
                "Filename,Experiment,Set,Type\nplate.jpg,E1,A,YPDA\n",
                encoding="utf-8",
            )

            class Result:
                returncode = 0
                stdout = "ready\n"
                stderr = ""

            with patch.object(batch_adapter, "PENDING_IMAGES_CSV", pending), patch.object(
                batch_adapter.subprocess, "run", return_value=Result()
            ) as run:
                count = batch_adapter.run_preflight()

            self.assertEqual(count, 1)
            command = run.call_args.args[0]
            self.assertIn("--no-fiji-handoff-path-rules", command)


if __name__ == "__main__":
    unittest.main()

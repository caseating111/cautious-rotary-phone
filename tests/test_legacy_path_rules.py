from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_four_point_batch_from_config as batch_adapter


class LegacyPathRuleTests(unittest.TestCase):
    def test_legacy_config_can_skip_only_composed_semicolon_path_rule(self) -> None:
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
                with self.assertRaises(SystemExit) as caught:
                    batch_adapter.load_config(require_fiji=False)
                self.assertIn("composed Fiji macro-argument delimiter", str(caught.exception))

                loaded = batch_adapter.load_config(
                    require_fiji=False,
                    require_fiji_handoff_paths=False,
                )

            self.assertEqual(loaded["crop_output"], str(root / "crop;output"))
            self.assertEqual(loaded["grid_csv"], str(root / "grid;metadata.csv"))

    def test_legacy_preflight_command_uses_non_composed_path_mode(self) -> None:
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
                count = batch_adapter.run_preflight(require_fiji_handoff_paths=False)

            self.assertEqual(count, 1)
            command = run.call_args.args[0]
            self.assertIn("--no-fiji-handoff-path-rules", command)


if __name__ == "__main__":
    unittest.main()

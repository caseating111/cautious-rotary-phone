from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import preflight_batch


class PreflightPathModeTests(unittest.TestCase):
    def test_cli_config_loader_can_disable_only_composed_path_delimiter_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "config.json"
            config.write_text(
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

            with self.assertRaises(SystemExit) as caught:
                preflight_batch.load_config(config)
            self.assertIn("composed Fiji macro-argument delimiter", str(caught.exception))

            loaded = preflight_batch.load_config(
                config,
                require_fiji_handoff_paths=False,
            )

            self.assertEqual(loaded["grid_csv"], str(root / "grid;metadata.csv"))
            self.assertEqual(loaded["crop_output"], str(root / "crop;output"))
            self.assertEqual(loaded["crop_width"], 130)
            self.assertEqual(loaded["crop_height"], 546)

    def test_malformed_config_fails_cleanly_without_json_traceback_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            config.write_text("{not valid json", encoding="utf-8")

            with self.assertRaises(SystemExit) as caught:
                preflight_batch.load_config(config)

            self.assertIn("Could not read config.json", str(caught.exception))

    def test_non_object_config_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            config.write_text(json.dumps(["not", "settings"]), encoding="utf-8")

            with self.assertRaises(SystemExit) as caught:
                preflight_batch.load_config(config)

            self.assertEqual(
                str(caught.exception),
                "config.json must contain a JSON object of named settings.",
            )


if __name__ == "__main__":
    unittest.main()

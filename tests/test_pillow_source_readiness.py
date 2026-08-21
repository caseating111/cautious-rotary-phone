from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import run_existing_pillow_from_config as pillow_adapter


class PillowSourceReadinessTests(unittest.TestCase):
    def test_standalone_pillow_config_without_image_root_skips_source_preflight(self) -> None:
        with patch.object(pillow_adapter, "build_batch_report") as report:
            pillow_adapter.validate_source_readiness_if_configured({"crop_output": "crops"})
        report.assert_not_called()

    def test_pending_source_plate_blocks_final_pillow_output(self) -> None:
        config = {"image_root": "images"}
        with patch.object(
            pillow_adapter,
            "build_batch_report",
            return_value=(["BATCH PREFLIGHT", "Images still requiring batch work: 1"], False, [{"Filename": "plate.jpg"}]),
        ):
            with self.assertRaises(SystemExit) as caught:
                pillow_adapter.validate_source_readiness_if_configured(config)
        self.assertIn("still needing crop generation/rebuild", str(caught.exception))

    def test_complete_source_crop_state_allows_pillow_output(self) -> None:
        config = {"image_root": "images"}
        with patch.object(
            pillow_adapter,
            "build_batch_report",
            return_value=(["BATCH PREFLIGHT", "Already complete images: 1"], False, []),
        ):
            pillow_adapter.validate_source_readiness_if_configured(config)

    def test_blocking_preflight_problem_stops_pillow_output(self) -> None:
        config = {"image_root": "images"}
        with patch.object(
            pillow_adapter,
            "build_batch_report",
            return_value=(["BATCH PREFLIGHT", "DUPLICATE SOURCE BASENAMES (1)"], True, []),
        ):
            with self.assertRaises(SystemExit) as caught:
                pillow_adapter.validate_source_readiness_if_configured(config)
        self.assertIn("blocking issues", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

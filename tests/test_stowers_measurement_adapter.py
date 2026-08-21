from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MACRO = REPO_ROOT / "fiji" / "stowers_measure_current_alignment.ijm"
CONTROLLER = REPO_ROOT / "tools" / "workflow_controller.py"


class StowersMeasurementAdapterTests(unittest.TestCase):
    def test_adapter_reuses_accepted_geometry_without_guessing_measurement_settings(self) -> None:
        text = MACRO.read_text(encoding="utf-8")

        self.assertIn('last_alignment.txt', text)
        self.assertIn('alignmentMatchesCurrentImage', text)
        self.assertIn('row_1_left_y', text)
        self.assertIn('row_" + gridRows + "_right_y', text)
        self.assertIn('makePolygon(', text)
        self.assertIn('leftX, leftTopY', text)
        self.assertIn('rightX, rightTopY', text)
        self.assertIn('rightX, rightBottomY', text)
        self.assertIn('leftX, leftBottomY', text)
        self.assertIn('spots = gridCols * gridRows;', text)
        self.assertIn('xyRatio = gridCols / gridRows;', text)
        self.assertIn('Spot radius, replicate grouping and background settings are assay-specific', text)
        self.assertIn('run("plate analysis jru v1");', text)

        # Keep the proof interactive: no scripted GenericDialog options until a
        # representative plate establishes scientifically sensible settings.
        self.assertNotIn('run("plate analysis jru v1",', text)

    def test_proof_is_not_exposed_as_controller_production_action(self) -> None:
        controller = CONTROLLER.read_text(encoding="utf-8")
        self.assertNotIn("stowers_measure_current_alignment", controller)
        self.assertNotIn("plate analysis jru v1", controller)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib
import unittest

from tools.applets.registry import APPLETS, validate_registry
from tools.applets.annotation import derive_annotation_positions
from tools.applets.plate_crop import calibrate_crop_size
from tools.applets.plate_layout import derive_plate_layout_from_spec, validate_plate_layout
from tools.applets.plate_orientation import compute_line_angle
from tools.applets.visibility import calculate_grid_roi


class AppletIntegrationTests(unittest.TestCase):
    def test_registry_contracts_and_keys_are_valid(self) -> None:
        validate_registry()
        self.assertEqual(len({applet.key for applet in APPLETS}), len(APPLETS))

    def test_every_integrated_applet_module_imports(self) -> None:
        for applet in APPLETS:
            with self.subTest(applet=applet.key):
                importlib.import_module(applet.module)

    def test_grid_consumers_declare_grid_prerequisite(self) -> None:
        prerequisites = {applet.key: applet.prerequisite for applet in APPLETS}
        self.assertEqual(prerequisites["visibility"], "accepted grid coordinates")
        self.assertEqual(prerequisites["annotation"], "accepted grid coordinates")

    def test_geometry_cores_preserve_reviewed_contracts(self) -> None:
        observed, correction = compute_line_angle(100, 100, 1000, 150)
        self.assertAlmostEqual(observed, 3.18, places=2)
        self.assertEqual(correction, observed)

        crop = calibrate_crop_size((100, 500), (2080, 600), (1000, 50), (1100, 2070), increment=50)
        self.assertEqual(crop["side_pixels"], 1950)

        roi = calculate_grid_roi([(100, 100), (900, 100), (100, 700), (900, 700)], max_width=1000, max_height=1000)
        self.assertEqual((roi["x"], roi["y"], roi["right"], roi["bottom"]), (80.0, 80.0, 920.0, 720.0))

    def test_layout_output_drives_annotation_without_rederiving_grid(self) -> None:
        vertical = [{"pos": row, "label": f"R{row}"} for row in range(1, 9)]
        bands = [{
            "order": 1,
            "profile": "P1",
            "labels": [{"pos": col, "label": f"S{col}"} for col in range(1, 11)],
        }]
        layout = derive_plate_layout_from_spec("proof", vertical, bands)
        self.assertTrue(validate_plate_layout(layout))
        grid = {(row, col): (100.0 + 60 * (col - 1), 100.0 + 60 * (row - 1)) for row in range(1, 9) for col in range(1, 11)}
        positions = derive_annotation_positions(layout, grid)
        self.assertEqual(len(positions["vertical_placements"]), 8)
        self.assertEqual(len(positions["strain_placements"]), 10)


if __name__ == "__main__":
    unittest.main()

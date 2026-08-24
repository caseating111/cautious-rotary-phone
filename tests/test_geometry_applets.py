from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.applets.plate_crop import (
    apply_plate_crop,
    calibrate_crop_size,
    place_plate_crop,
    transform_point_from_crop_to_source,
    transform_point_to_crop,
)
from tools.applets.plate_orientation import (
    apply_plate_orientation,
    capture_plate_orientation,
    compute_line_angle,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OrientationAppletTests(unittest.TestCase):
    def test_angle_convention_handles_both_slopes_and_near_zero(self) -> None:
        observed, correction = compute_line_angle(0, 0, 100, 10)
        self.assertAlmostEqual(observed, 5.710593, places=5)
        self.assertEqual(correction, observed)
        observed, correction = compute_line_angle(0, 10, 100, 0)
        self.assertAlmostEqual(observed, -5.710593, places=5)
        self.assertEqual(correction, observed)
        self.assertAlmostEqual(compute_line_angle(0, 2, 100, 2)[1], 0.0)

    def test_proposed_is_preview_only_and_accept_is_non_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            output = root / "derived" / "oriented.png"
            Image.new("L", (200, 160), 64).save(source)
            source_hash = _digest(source)
            proposed = capture_plate_orientation(
                (10, 20, 190, 30),
                {"width": 200, "height": 160},
                {"image_uid": "img-1"},
            )
            self.assertEqual(proposed["status"], "PROPOSED")
            self.assertEqual(apply_plate_orientation(source, proposed).size, (200, 160))
            with self.assertRaisesRegex(ValueError, "before acceptance"):
                apply_plate_orientation(source, proposed, output)

            accepted = capture_plate_orientation(
                (10, 20, 190, 30),
                {"width": 200, "height": 160},
                {"image_uid": "img-1", "accepted": True},
            )
            self.assertEqual(accepted["transform"]["source_dimensions"], [200, 160])
            self.assertEqual(accepted["transform"]["output_dimensions"], [200, 160])
            self.assertEqual(
                Path(apply_plate_orientation(source, accepted, output)), output
            )
            with Image.open(output) as image:
                self.assertEqual(image.size, (200, 160))
            self.assertEqual(_digest(source), source_hash)

    def test_skip_supports_path_input_and_exact_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            output = root / "skipped.png"
            Image.new("RGB", (24, 16), (1, 2, 3)).save(source)
            result = capture_plate_orientation(
                None,
                {"width": 24, "height": 16},
                {"image_uid": "img-1", "skip": True},
            )
            apply_plate_orientation(source, result, output)
            self.assertEqual(output.read_bytes(), source.read_bytes())


class CropAppletTests(unittest.TestCase):
    def _accepted_calibration(self) -> dict:
        return calibrate_crop_size((10, 0), (143, 0), (0, 5), (0, 176), accepted=True)

    def test_calibration_rounding_reuse_bounds_and_transforms(self) -> None:
        calibration = self._accepted_calibration()
        self.assertEqual(calibration["side_pixels"], 100)
        first = place_plate_crop(
            calibration,
            (10, 0),
            (0, 20),
            {"width": 220, "height": 180},
            options={"accepted": True, "image_uid": "img-1"},
        )
        second = place_plate_crop(
            calibration,
            (30, 0),
            (0, 40),
            {"width": 220, "height": 180},
            options={"accepted": True, "image_uid": "img-2"},
        )
        self.assertNotEqual(first["crop_box"], second["crop_box"])
        cropped = transform_point_to_crop(15, 27, first)
        self.assertEqual(transform_point_from_crop_to_source(*cropped, first), (15, 27))
        with self.assertRaisesRegex(ValueError, "outside source dimensions"):
            place_plate_crop(
                calibration,
                (150, 0),
                (0, 100),
                {"width": 220, "height": 180},
                options={"accepted": True},
            )

    def test_proposed_is_preview_only_and_orientation_output_feeds_crop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            oriented = root / "oriented.png"
            cropped = root / "crop.png"
            Image.new("L", (220, 180), 128).save(source)
            source_hash = _digest(source)
            orientation = capture_plate_orientation(
                (10, 20, 210, 30),
                {"width": 220, "height": 180},
                {"accepted": True, "image_uid": "img-1"},
            )
            apply_plate_orientation(source, orientation, oriented)

            calibration = self._accepted_calibration()
            proposed = place_plate_crop(
                calibration,
                (20, 0),
                (0, 30),
                {"width": 220, "height": 180},
            )
            self.assertEqual(apply_plate_crop(oriented, proposed).size, (100, 100))
            with self.assertRaisesRegex(ValueError, "before acceptance"):
                apply_plate_crop(oriented, proposed, cropped)
            accepted = place_plate_crop(
                calibration,
                (20, 0),
                (0, 30),
                {"width": 220, "height": 180},
                options={"accepted": True, "image_uid": "img-1"},
            )
            apply_plate_crop(oriented, accepted, cropped)
            with Image.open(cropped) as image:
                self.assertEqual(image.size, (100, 100))
            self.assertEqual(_digest(source), source_hash)


if __name__ == "__main__":
    unittest.main()

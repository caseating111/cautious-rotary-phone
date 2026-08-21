from __future__ import annotations

import unittest

from tools.run_fiji_macro_from_config import build_command, visibility_argument


class FijiLauncherTests(unittest.TestCase):
    def test_visibility_argument_uses_configured_values(self) -> None:
        config = {
            "visibility_band": 40,
            "visibility_black_offset": 2.5,
            "visibility_high_percentile": 99.2,
        }
        self.assertEqual(
            visibility_argument(config),
            "band=40;black_offset=2.5;high_percentile=99.2",
        )

    def test_visibility_command_uses_imagej_macro_argument_position(self) -> None:
        config = {
            "fiji_executable": "C:/Fiji/ImageJ-win64.exe",
            "visibility_band": 50,
            "visibility_black_offset": 3,
            "visibility_high_percentile": 99.5,
        }
        command = build_command(config)
        self.assertEqual(command[0], "C:/Fiji/ImageJ-win64.exe")
        self.assertEqual(command[1], "-macro")
        self.assertTrue(command[2].endswith("apply_global_visibility_and_archive.ijm"))
        self.assertEqual(
            command[3],
            "band=50;black_offset=3;high_percentile=99.5",
        )

    def test_visibility_settings_reject_invalid_percentile(self) -> None:
        with self.assertRaises(SystemExit):
            visibility_argument({"visibility_high_percentile": 0})

    def test_visibility_settings_reject_non_finite_values(self) -> None:
        for key, value in (
            ("visibility_band", "NaN"),
            ("visibility_black_offset", "inf"),
            ("visibility_high_percentile", "-inf"),
        ):
            with self.subTest(key=key, value=value):
                with self.assertRaises(SystemExit) as caught:
                    visibility_argument({key: value})
                self.assertIn("finite numbers", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

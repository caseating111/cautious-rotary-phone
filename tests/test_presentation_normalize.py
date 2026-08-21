from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.presentation_normalize import display_map, load_range, normalize_staged_crops


class PresentationNormalizeTests(unittest.TestCase):
    def test_display_map_uses_archived_black_high_range(self) -> None:
        image = Image.new("L", (3, 1))
        image.putdata([10, 60, 110])
        mapped = display_map(image, 10, 110)
        self.assertEqual([mapped.getpixel((x, 0)) for x in range(3)], [0, 128, 255])

    def test_range_identity_mismatch_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "plate1.jpg.txt"
            path.write_text(
                "source_filename=plate2.jpg\nblack_point=10\nhigh_point=110\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit) as caught:
                load_range(root, "plate1.jpg")
            self.assertIn("identity mismatch", str(caught.exception))

    def test_range_older_than_current_source_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plate1.jpg"
            source.write_bytes(b"source")
            archive = root / "plate1.jpg.txt"
            archive.write_text(
                "source_filename=plate1.jpg\nblack_point=10\nhigh_point=110\n",
                encoding="utf-8",
            )
            os.utime(archive, ns=(1_000_000_000, 1_000_000_000))
            os.utime(source, ns=(2_000_000_000, 2_000_000_000))

            with self.assertRaises(SystemExit) as caught:
                load_range(root, "plate1.jpg", source_path=source)
            self.assertIn("older than the current source image", str(caught.exception))

    def test_normalization_changes_only_staged_crop_using_source_plate_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            staged = root / "staged"
            ranges = root / "ranges"
            staged.mkdir()
            ranges.mkdir()
            grid = root / "grid.csv"
            images = root / "images.csv"
            grid.write_text(
                "Experiment,Set,GridCols,Column,Strain\nE2,A,1,1,WT\n",
                encoding="utf-8",
            )
            images.write_text(
                "Filename,Experiment,Set,Type\nplate1.jpg,E2,A,YPDA\n",
                encoding="utf-8",
            )
            crop = staged / "E2_A_YPDA_01_Top_WT.png"
            image = Image.new("L", (3, 1))
            image.putdata([10, 60, 110])
            image.save(crop)
            ranges.joinpath("plate1.jpg.txt").write_text(
                "source_filename=plate1.jpg\nblack_point=10\nhigh_point=110\n",
                encoding="utf-8",
            )

            count = normalize_staged_crops([crop], grid, images, ranges)
            self.assertEqual(count, 1)
            with Image.open(crop) as normalized:
                self.assertEqual([normalized.getpixel((x, 0)) for x in range(3)], [0, 128, 255])


if __name__ == "__main__":
    unittest.main()
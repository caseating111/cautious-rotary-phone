from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import custom_crop_inventory as inventory
from tools import custom_matrix_selection as custom


class PresentationRangeInventoryTests(unittest.TestCase):
    def item(self, source: str) -> inventory.CropInventoryItem:
        return inventory.CropInventoryItem(
            experiment="E1",
            set_name="A",
            condition="YPDA",
            column=1,
            strain="WT",
            state="Top",
            source_filename=source,
            expected_filename="crop.png",
            status="current",
        )

    def test_reports_ready_and_missing_ranges_per_unique_source_plate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_root = root / "images"
            source_folder = image_root / "setA"
            ranges = root / "app" / "display-ranges"
            source_folder.mkdir(parents=True)
            ranges.mkdir(parents=True)
            source1 = source_folder / "plate1.jpg"
            source2 = source_folder / "plate2.jpg"
            source1.write_bytes(b"one")
            source2.write_bytes(b"two")
            archive = ranges / "plate1.jpg.txt"
            archive.write_text(
                "source_filename=plate1.jpg\nblack_point=10\nhigh_point=200\n",
                encoding="utf-8",
            )
            future = max(source1.stat().st_mtime_ns, archive.stat().st_mtime_ns) + 10_000_000
            os.utime(archive, ns=(future, future))

            with patch.object(custom, "APP_DIR", root / "app"):
                ready, issues = inventory.presentation_range_issues(
                    {"image_root": str(image_root)},
                    [self.item("plate1.jpg"), self.item("plate1.jpg"), self.item("plate2.jpg")],
                )

            self.assertEqual(ready, 1)
            self.assertEqual(len(issues), 1)
            self.assertIn("plate2.jpg", issues[0])
            self.assertIn("No archived Fiji display range", issues[0])

    def test_stale_archive_is_not_counted_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_root = root / "images"
            source_folder = image_root / "setA"
            ranges = root / "app" / "display-ranges"
            source_folder.mkdir(parents=True)
            ranges.mkdir(parents=True)
            source = source_folder / "plate1.jpg"
            source.write_bytes(b"one")
            archive = ranges / "plate1.jpg.txt"
            archive.write_text(
                "source_filename=plate1.jpg\nblack_point=10\nhigh_point=200\n",
                encoding="utf-8",
            )
            future = max(source.stat().st_mtime_ns, archive.stat().st_mtime_ns) + 10_000_000
            os.utime(source, ns=(future, future))

            with patch.object(custom, "APP_DIR", root / "app"):
                ready, issues = inventory.presentation_range_issues(
                    {"image_root": str(image_root)},
                    [self.item("plate1.jpg")],
                )

            self.assertEqual(ready, 0)
            self.assertEqual(len(issues), 1)
            self.assertIn("older than the current source image", issues[0])


if __name__ == "__main__":
    unittest.main()

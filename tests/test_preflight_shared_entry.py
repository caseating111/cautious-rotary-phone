from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.preflight_batch import build_report


class SharedPreflightEntryTests(unittest.TestCase):
    def test_build_report_rejects_crop_tree_inside_source_tree_for_all_callers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_root = root / "images"
            source_folder = image_root / "setA"
            crop_root = image_root / "derived"
            source_folder.mkdir(parents=True)
            crop_root.mkdir()
            (source_folder / "plate1.jpg").write_bytes(b"placeholder")

            grid_csv = root / "grid.csv"
            images_csv = root / "images.csv"
            grid_csv.write_text(
                "Experiment,Set,GridCols,Column,Strain\n"
                "E1,A,2,1,WT\n"
                "E1,A,2,2,mut2\n",
                encoding="utf-8",
            )
            images_csv.write_text(
                "Filename,Experiment,Set,Type\n"
                "plate1.jpg,E1,A,YPDA\n",
                encoding="utf-8",
            )
            config = {
                "image_root": str(image_root),
                "crop_output": str(crop_root),
                "grid_csv": str(grid_csv),
                "images_csv": str(images_csv),
                "crop_width": 130,
                "crop_height": 546,
            }

            for kwargs in (
                {},
                {"require_alignment_geometry": False, "require_fiji_handoff_paths": False},
            ):
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(SystemExit) as caught:
                        build_report(config, **kwargs)
                    self.assertIn("crop_output must be outside image_root", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

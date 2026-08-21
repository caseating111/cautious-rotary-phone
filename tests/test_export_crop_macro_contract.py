from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_MACRO = REPO_ROOT / "fiji" / "export_crops_from_alignment.ijm"


class ExportCropMacroContractTests(unittest.TestCase):
    def test_identity_and_complete_geometry_are_validated_before_first_png_save(self) -> None:
        text = EXPORT_MACRO.read_text(encoding="utf-8")

        identity_at = text.index("alignmentMatchesCurrentImage(")
        duplicate_guard_at = text.index('exit("Duplicate grid column "')
        bounds_guard_at = text.index("if (!cropFitsImage(cx, topY")
        complete_grid_at = text.index("if (matched != gridCols)")
        first_save_at = text.index('saveAs("PNG"')

        self.assertLess(identity_at, first_save_at)
        self.assertLess(duplicate_guard_at, first_save_at)
        self.assertLess(bounds_guard_at, first_save_at)
        self.assertLess(complete_grid_at, first_save_at)
        self.assertIn("No crops were exported", text[:first_save_at])

    def test_export_count_and_top_low_naming_match_existing_contract(self) -> None:
        text = EXPORT_MACRO.read_text(encoding="utf-8")

        self.assertIn('"_Top_" + safeName(strain)', text)
        self.assertIn('"_Low_" + safeName(strain)', text)
        self.assertIn("exported = exported + 2;", text)
        self.assertIn("if (exported != gridCols * 2)", text)
        self.assertIn("source_directory", text)
        self.assertIn("source_filename", text)

    def test_source_image_is_duplicated_for_each_derived_crop(self) -> None:
        text = EXPORT_MACRO.read_text(encoding="utf-8")
        export_fn_at = text.index("function exportCrop(")
        export_fn = text[export_fn_at:]

        self.assertIn("selectWindow(sourceTitle);", export_fn)
        self.assertIn('run("Duplicate...", "title=[" + outputName + "]");', export_fn)
        self.assertIn('saveAs("PNG", outDir + outputName + ".png");', export_fn)
        self.assertIn("close();", export_fn)
        self.assertNotIn('run("Crop")', export_fn)


if __name__ == "__main__":
    unittest.main()

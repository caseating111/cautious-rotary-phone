from __future__ import annotations

import unittest

from tools import run_four_point_batch_from_config as batch


class FourPointMathematicalQCTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = batch.SOURCE_MACRO.read_text(encoding="utf-8")

    def test_enhanced_route_preserves_four_anchor_geometry_and_fixed_crop_export(self) -> None:
        text = batch.enhance_four_point_macro(self.source)
        for label in ("R1C1", "R1C\" + gridCols", "R5C1", "R5C\" + gridCols"):
            self.assertIn(label, text)
        self.assertIn("TOP_FACTOR = 0.375;", text)
        self.assertIn("LOW_FACTOR = 1.375;", text)
        self.assertIn("CROP_W", text)
        self.assertIn("CROP_H", text)

    def test_alignment_view_is_disposable_and_uses_whole_image_double_clahe(self) -> None:
        text = batch.enhance_four_point_macro(self.source)
        self.assertIn('run("Duplicate...", "title=__alignment_view__")', text)
        self.assertIn('run("Select None")', text)
        self.assertEqual(text.count('run("Enhance Local Contrast (CLAHE)", claheOptions)'), 2)
        self.assertNotIn("sampleW =", text)
        self.assertNotIn('run("Enhance Contrast", "saturated=0.35")', text)
        self.assertIn('selectWindow(sourceTitle);', text)

    def test_full_grid_qc_is_pure_math_and_runs_before_export(self) -> None:
        text = batch.enhance_four_point_macro(self.source)
        qc = text.index('Dialog.create("Full-grid QC --')
        export = text.index("// EXPORT CROPS", qc)
        self.assertLess(qc, export)
        self.assertIn("for (qcRow = 1; qcRow <= 8; qcRow++)", text)
        self.assertIn("for (qcCol = 1; qcCol <= gridCols; qcCol++)", text)
        self.assertIn("v = (qcRow - 1) / 4;", text)
        self.assertIn("u = (qcCol - 1) / (gridCols - 1);", text)
        self.assertIn('newArray("ACCEPT", "RETRY")', text)
        self.assertNotIn("Array.findMaxima", text)
        self.assertNotIn("getProfile()", text)

    def test_qc_retry_marker_overrides_awt_default_accept(self) -> None:
        text = batch.enhance_four_point_macro(self.source)
        choice = text.index("qcAction = Dialog.getChoice();")
        accept = text.index('if (qcAction == "ACCEPT")', choice)
        retry_override = text.index('if (hotkeyAction == "retry")', choice)
        self.assertLess(retry_override, accept)
        self.assertIn("String.trim(File.openAsString(controlFile))", text)
        self.assertIn('qcAction = "RETRY";', text[retry_override:accept])
        self.assertIn("File.delete(controlFile);", text[retry_override:accept])

    def test_ahk_persists_qc_retry_before_driving_awt_choice(self) -> None:
        ahk = (
            batch.REPO_ROOT / "ahk" / "four_point_alignment_hotkeys.ah2"
        ).read_text(encoding="utf-8")
        handler = ahk[
            ahk.index('#HotIf FijiWorkflowDialog("Alignment QC")') :
        ]
        write = handler.index('WriteBatchControl("retry")')
        send = handler.index('Send("{Home}{Down}{Enter}")')
        self.assertLess(write, send)
        self.assertIn('FileAppend(action, controlPath, "UTF-8-RAW")', ahk)

    def test_successful_export_records_reusable_grid_after_state_commit(self) -> None:
        configured = batch.configure_source_settings(
            self.source,
            {
                "grid_csv": "C:/metadata/grid.csv",
                "image_root": "C:/raw",
                "crop_output": "C:/crops",
                "crop_width": 130,
                "crop_height": 546,
            },
            run_label="Single",
        )
        text = batch.enhance_four_point_macro(configured)
        state_commit = text.index('File.append(stateKey + "\\t" + runNumber')
        grid_commit = text.index('File.append(gridLine + "\\n", gridCoordinateHandoff);')
        self.assertLess(state_commit, grid_commit)
        self.assertIn('gridRunLabel = "Single";', text)
        self.assertIn('"\\t8\\t" + gridCols', text)

if __name__ == "__main__":
    unittest.main()

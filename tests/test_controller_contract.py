from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.workflow_controller import PROJECT_CSV_FILES, preflight_dialog_text, sibling_project_csvs


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = REPO_ROOT / "tools" / "workflow_controller.py"
AHK_HELPER = REPO_ROOT / "ahk" / "four_point_alignment_hotkeys.ah2"


class ControllerContractTests(unittest.TestCase):
    def test_pillow_outputs_are_centralized_in_the_matrix_applet(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        self.assertIn('text="Build matrices and labelled crops"', text)
        self.assertIn('self.launch_python("tools/custom_matrix_gui_recorded.py")', text)
        self.assertNotIn("PILLOW_JOBS", text)
        self.assertNotIn("def run_pillow_job", text)
    def test_processing_settings_are_current_crop_dimensions_only(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        settings = text[text.index("PROCESSING_SETTINGS"):text.index("def load_config_state")]
        self.assertIn("Crop width", settings)
        self.assertIn("Crop height", settings)
        self.assertNotIn("Visibility", settings)
        self.assertNotIn("Alignment peak tolerance", settings)
        block = text[text.index("def open_processing_settings"):text.index("def batch_preflight_result")]
        self.assertIn('int(self.vars["crop_width"].get())', block)
        self.assertIn("Crop dimensions must be positive integers.", block)

    def test_hotkeys_cover_current_four_click_qc_and_lifecycle(self) -> None:
        text = AHK_HELPER.read_text(encoding="utf-8")
        for title in ("1 / 4", "2 / 4", "3 / 4", "4 / 4", "Full-grid QC", "ALL DONE"):
            self.assertIn(f'"{title}"', text)
        self.assertIn("#HotIf AlignmentDialogExists()", text)
        self.assertIn("z::", text)
        self.assertIn("x::", text)
        self.assertIn("c::", text)
        self.assertIn("Esc::", text)
        self.assertIn('WriteBatchControl("restart")', text)

    def test_ahk_preserves_scoped_window_hotfixes(self) -> None:
        text = AHK_HELPER.read_text(encoding="utf-8")
        self.assertIn("WorkflowWindowWatchDeadline := A_TickCount + 10000", text)
        self.assertIn('WinGetList("ahk_class SunAwtFrame ahk_exe fiji-windows-x64.exe")', text)
        self.assertNotIn('WinGetList("ahk_class SunAwtFrame")', text)
        self.assertIn('WinSetAlwaysOnTop(0, "ahk_id " hwnd)', text)
        self.assertIn('WinMoveBottom("ahk_id " hwnd)', text)
        self.assertIn("WinHide(", text)
        self.assertIn("WinClose(", text)
        self.assertIn("DuplicatePromptDeadline := A_TickCount + 1800", text)
        self.assertIn("WinMove(x, top + 10, , , bestHwnd)", text)

    def test_preflight_dialog_summary_uses_saved_report(self) -> None:
        long_output = "BATCH PREFLIGHT\n" + ("detail line\n" * 200)
        ready = preflight_dialog_text(0, 7, long_output, report_exists=True)
        self.assertIn("Pending images: 7", ready)
        self.assertNotIn("detail line", ready)
        self.assertEqual(preflight_dialog_text(1, 0, "Config not found", report_exists=False), "Config not found")

    def test_project_csv_sibling_discovery_uses_exact_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            grid = root / "grid.csv"
            images = root / "images.csv"
            grid.write_text("grid\n", encoding="utf-8")
            images.write_text("images\n", encoding="utf-8")
            found = sibling_project_csvs(grid)
        self.assertEqual(found["grid_csv"], grid)
        self.assertEqual(found["images_csv"], images)
        self.assertEqual(PROJECT_CSV_FILES["condition_order_csv"], "condition_order.csv")


if __name__ == "__main__":
    unittest.main()

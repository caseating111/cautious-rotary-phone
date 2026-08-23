from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.workflow_controller import (
    PROJECT_CSV_FILES,
    preflight_dialog_text,
    sibling_project_csvs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = REPO_ROOT / "tools" / "workflow_controller.py"
AHK_HELPER = REPO_ROOT / "ahk" / "full_column_alignment_hotkeys.ah2"


class ControllerContractTests(unittest.TestCase):
    def test_pillow_failures_are_checked(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        pillow_at = text.index("def run_pillow_job")
        pillow_block = text[pillow_at : text.index("def start_ahk", pillow_at)]
        self.assertIn("subprocess.run(", pillow_block)
        self.assertIn("capture_output=True", pillow_block)
        self.assertIn("messagebox.showerror", pillow_block)
        self.assertNotIn("self.launch_python", pillow_block)

    def test_controller_does_not_expose_retired_batch_routes(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        self.assertNotIn('text="Run 4-point fallback"', text)
        self.assertNotIn("def run_prepared_batch", text)
        self.assertNotIn("def launch_fiji_macro", text)

    def test_controller_exposes_saved_preflight_report(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        self.assertIn('PREFLIGHT_REPORT = APP_DIR / "last_preflight.txt"', text)
        self.assertIn('text="Open last preflight report"', text)
        self.assertIn("command=self.open_preflight_report", text)
        self.assertIn('self.open_existing_path(PREFLIGHT_REPORT, "Preflight report")', text)
        self.assertIn("Open the saved report for easier review.", text)

    def test_preflight_dialog_summary_avoids_repeating_long_saved_report(self) -> None:
        long_output = "BATCH PREFLIGHT\n" + ("detail line\n" * 200)

        ready = preflight_dialog_text(0, 7, long_output, report_exists=True)
        self.assertIn("Pending images: 7", ready)
        self.assertIn("Full details are saved", ready)
        self.assertNotIn("detail line", ready)

        blocked = preflight_dialog_text(1, 0, long_output, report_exists=True)
        self.assertIn("Preflight found blocking items", blocked)
        self.assertIn("Open the saved preflight report", blocked)
        self.assertNotIn("detail line", blocked)

        raw_failure = preflight_dialog_text(1, 0, "Config not found", report_exists=False)
        self.assertEqual(raw_failure, "Config not found")

        stale_report_failure = preflight_dialog_text(
            1,
            0,
            "CSV validation FAILED\n- bad metadata",
            report_exists=True,
        )
        self.assertEqual(stale_report_failure, "CSV validation FAILED\n- bad metadata")

    def test_processing_settings_reject_non_finite_values_before_save(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        settings_at = text.index("def open_processing_settings")
        settings_block = text[settings_at : text.index("def batch_preflight_result", settings_at)]

        self.assertIn("math.isfinite", settings_block)
        self.assertIn("Processing settings must be finite numbers.", settings_block)
        self.assertLess(settings_block.index("math.isfinite"), settings_block.index("self.save("))

    def test_single_hotkey_helper_covers_full_column_and_four_point_dialogs(self) -> None:
        text = AHK_HELPER.read_text(encoding="utf-8")
        for title in ("1 / 2", "2 / 2", "Alignment QC", "Full-grid QC", "1 / 4", "2 / 4", "3 / 4", "4 / 4", "ALL DONE"):
            self.assertIn(f'"{title}"', text)
        self.assertIn('#HotIf WinExist("Alignment QC") || WinExist("Full-grid QC")', text)
        self.assertIn("Esc::ExitApp", text)

    def test_hotkey_shell_hook_only_moves_new_placement_dialogs(self) -> None:
        text = AHK_HELPER.read_text(encoding="utf-8")
        shell_at = text.index("ShellMessage(")
        timer_at = text.index("StartPlacementCatchup()", shell_at)
        shell_block = text[shell_at:timer_at]

        self.assertIn("HSHELL_WINDOWCREATED = 1", shell_block)
        self.assertIn("PlacementDialogTitle(title)", shell_block)
        self.assertIn("WinMove(10, 10", shell_block)
        self.assertNotIn("Send(", shell_block)
        self.assertNotIn("WinActivate", shell_block)

    def test_hotkey_uses_bounded_catchup_and_suppresses_launcher_overlay(self) -> None:
        text = AHK_HELPER.read_text(encoding="utf-8")
        self.assertIn("PlacementCatchupDeadline := A_TickCount + 3000", text)
        self.assertIn("SetTimer(CatchUpWorkflowWindows, 120)", text)
        self.assertIn("SetTimer(CatchUpWorkflowWindows, 0)", text)
        self.assertIn('InStr(title, "Launching Fiji")', text)
        self.assertIn("WinSetAlwaysOnTop(0, hwnd)", text)
        self.assertIn("WinMoveBottom(hwnd)", text)
        self.assertIn("WinHide(hwnd)", text)
        self.assertNotIn("DetectHiddenWindows True", text)
        self.assertIn("MoveFijiToolbarOnce()", text)
        self.assertIn('className != "SunAwtFrame"', text)
        self.assertNotIn("w < 640 || h < 160", text)
        self.assertNotIn("h := Min(180, bottom - top)", text)
        self.assertNotIn("WinShow(bestHwnd)", text)
        self.assertNotIn("WinRestore(bestHwnd)", text)
        self.assertIn("MonitorGetWorkArea", text)
        self.assertIn("right - w - 10", text)
        self.assertIn("WinMove(x, top + 10, , , bestHwnd)", text)
        self.assertIn("WinMove(10, 10", text)

    def test_project_csv_sibling_discovery_uses_only_exact_existing_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            grid = root / "grid.csv"
            images = root / "images.csv"
            unrelated = root / "condition-order.csv"
            grid.write_text("grid\n", encoding="utf-8")
            images.write_text("images\n", encoding="utf-8")
            unrelated.write_text("not the contract filename\n", encoding="utf-8")

            found = sibling_project_csvs(grid)

            self.assertEqual(found["grid_csv"], grid)
            self.assertEqual(found["images_csv"], images)
            self.assertNotIn("condition_order_csv", found)
            self.assertEqual(PROJECT_CSV_FILES["condition_order_csv"], "condition_order.csv")

    def test_csv_browse_autofill_only_targets_blank_sibling_fields(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        browse_at = text.index("def browse")
        browse_block = text[browse_at : text.index("def save", browse_at)]

        self.assertIn("if key in PROJECT_CSV_FILES:", browse_block)
        self.assertIn("sibling_project_csvs(Path(chosen))", browse_block)
        self.assertIn("self.vars[sibling_key].get().strip()", browse_block)
        self.assertIn("continue", browse_block)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.workflow_controller import PROJECT_CSV_FILES, sibling_project_csvs


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = REPO_ROOT / "tools" / "workflow_controller.py"
AHK_HELPER = REPO_ROOT / "ahk" / "full_column_alignment_hotkeys.ah2"


class ControllerContractTests(unittest.TestCase):
    def test_batch_prepares_before_hotkeys_and_pillow_failures_are_checked(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")

        prepare_at = text.index('"--prepare-only"')
        start_ahk_at = text.index("self.start_ahk()", prepare_at)
        self.assertLess(prepare_at, start_ahk_at)
        self.assertIn("started_ahk_here", text)
        self.assertIn("if started_ahk_here:", text)
        self.assertIn("self.stop_ahk()", text)

        pillow_at = text.index("def run_pillow_job")
        pillow_block = text[pillow_at : text.index("def start_ahk", pillow_at)]
        self.assertIn("subprocess.run(", pillow_block)
        self.assertIn("capture_output=True", pillow_block)
        self.assertIn("messagebox.showerror", pillow_block)
        self.assertNotIn("self.launch_python", pillow_block)

    def test_controller_exposes_preserved_four_point_fallback_through_same_prepare_path(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        prepared_at = text.index("def run_prepared_batch")
        prepared_block = text[prepared_at : text.index("def run_pillow_job", prepared_at)]

        self.assertIn('text="Run 4-point fallback"', text)
        self.assertIn('args.append("--legacy")', prepared_block)
        self.assertIn("CONFIGURED_LEGACY_BATCH_MACRO", prepared_block)
        self.assertIn("self.run_prepared_batch(legacy=False)", prepared_block)
        self.assertIn("self.run_prepared_batch(legacy=True)", prepared_block)
        self.assertIn("self.start_ahk()", prepared_block)

    def test_single_hotkey_helper_covers_full_column_and_four_point_dialogs(self) -> None:
        text = AHK_HELPER.read_text(encoding="utf-8")
        for title in ("1 / 2", "2 / 2", "Alignment QC", "1 / 4", "2 / 4", "3 / 4", "4 / 4", "ALL DONE"):
            self.assertIn(f'"{title}"', text)
        self.assertIn('#HotIf WinExist("Alignment QC")', text)
        self.assertIn("Esc::ExitApp", text)

    def test_hotkey_shell_hook_only_moves_new_placement_dialogs(self) -> None:
        text = AHK_HELPER.read_text(encoding="utf-8")
        shell_at = text.index("ShellMessage(")
        shell_block = text[shell_at : text.index("AlignmentDialogExists()", shell_at)]

        self.assertIn("HSHELL_WINDOWCREATED = 1", shell_block)
        self.assertIn("PlacementDialogTitle(title)", shell_block)
        self.assertIn("WinMove(10, 10", shell_block)
        self.assertNotIn("Send(", shell_block)
        self.assertNotIn("WinActivate", shell_block)

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

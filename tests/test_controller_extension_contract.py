from __future__ import annotations

import unittest
from pathlib import Path

from tools.workflow_controller_extended import path_is_within_windows_root


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTENDED = REPO_ROOT / "tools" / "workflow_controller_extended.py"


class ControllerExtensionContractTests(unittest.TestCase):
    def test_active_gui_exposes_current_workflow_endpoints(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        for label in (
            "Run all 4-point",
            "Run subfolder",
            "Run single image",
            "Rerun single image",
            "Build matrices and labelled crops",
            "Reconcile / validate CSV workflow",
        ):
            self.assertIn(f'text="{label}"', text)
        for retired in (
            "Custom matrices",
            "Preferred WT source",
            "Pillow output",
            "Global visibility",
            "Run full-column batch",
            "Run 4-point fallback",
        ):
            self.assertNotIn(f'text="{retired}"', text)

    def test_single_selection_is_root_scoped_and_rerun_forces_replacement(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        start = text.index("def run_one_plate_validation")
        end = text.index("\ndef main()", start)
        block = text[start:end]
        self.assertIn("path_is_within_windows_root(chosen_path, image_root)", block)
        self.assertIn("one_plate_validation.run_with_process(", block)
        self.assertIn("replace_existing=rerun_done or self.replace_existing_crops.get()", block)
        self.assertIn("authoritative prepare-only results remain available", block)

    def test_single_selection_containment_is_windows_case_insensitive(self) -> None:
        self.assertTrue(path_is_within_windows_root(r"C:\Data\Raw\Set\plate.jpg", r"c:\data\raw"))
        self.assertFalse(path_is_within_windows_root(r"C:\Data\Outside\plate.jpg", r"c:\data\raw"))

    def test_batch_checks_roi_patch_and_monitors_wrapper_result(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        start = text.index("def run_four_point_batch")
        end = text.index("def choose_csv_folder", start)
        block = text[start:end]
        self.assertIn("ensure_roi_click_patch", block)
        self.assertIn("monitor_batch_process", block)
        self.assertIn("process exit alone", block)
        self.assertNotIn("Pillow output complete", block)

    def test_outputs_have_one_unified_applet_route(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        self.assertEqual(text.count('self.launch_python("tools/custom_matrix_gui_recorded.py")'), 1)
        self.assertNotIn("PILLOW_JOBS", text)
        self.assertNotIn("def run_pillow_job", text)
        self.assertNotIn("dedup_control_gui.py", text)
        self.assertNotIn("preview_standard_outputs", text)
        self.assertIn('Path(raw) / "Processing Logs"', text)


if __name__ == "__main__":
    unittest.main()

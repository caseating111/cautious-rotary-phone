from __future__ import annotations

import unittest
from pathlib import Path


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
            "Custom matrices",
            "Preferred WT source",
            "Reconcile / validate CSV workflow",
        ):
            self.assertIn(f'text="{label}"', text)
        for retired in ("Global visibility", "Run full-column batch", "Run 4-point fallback"):
            self.assertNotIn(f'text="{retired}"', text)

    def test_single_selection_is_root_scoped_and_rerun_forces_replacement(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        start = text.index("def run_one_plate_validation")
        end = text.index("def standard_output_count", start)
        block = text[start:end]
        self.assertIn("chosen_path.relative_to(Path(image_root).resolve())", block)
        self.assertIn("one_plate_validation.run_with_process(", block)
        self.assertIn("replace_existing=rerun_done or self.replace_existing_crops.get()", block)
        self.assertIn("authoritative prepare-only results remain available", block)

    def test_batch_checks_roi_patch_and_monitors_wrapper_result(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        start = text.index("def run_four_point_batch")
        end = text.index("def choose_csv_folder", start)
        block = text[start:end]
        self.assertIn("ensure_roi_click_patch", block)
        self.assertIn("monitor_batch_process", block)
        self.assertIn("process exit alone", block)
        self.assertNotIn("Pillow output complete", block)

    def test_dedup_routes_to_explicit_control_selection_before_preview_opt_out(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        start = text.index("def run_pillow_job")
        block = text[start:]
        dedup = block.index('if alias == "all-strains-dedup":')
        opt_out = block.index("if not self.preview_standard_outputs.get():")
        self.assertLess(dedup, opt_out)
        self.assertIn('self.launch_python("tools/dedup_control_gui.py")', block[dedup:opt_out])

    def test_standard_outputs_keep_preview_and_processing_records(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        self.assertIn('self.config_bool("preview_standard_outputs", True)', text)
        self.assertIn("standard_pillow_preview.build_preview(alias)", text)
        self.assertIn("write_output_records(", text)
        self.assertIn('display_mode="raw"', text)
        self.assertIn('Path(raw) / "Processing Logs"', text)


if __name__ == "__main__":
    unittest.main()

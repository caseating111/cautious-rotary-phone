from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTENDED = REPO_ROOT / "tools" / "workflow_controller_extended.py"
STARTER = REPO_ROOT / "start_controller.cmd"


class ControllerExtensionContractTests(unittest.TestCase):
    def test_extended_controller_stays_thin_while_adding_utility_launchers(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        self.assertIn("class ExtendedController(Controller)", text)
        self.assertIn('text="Custom matrices"', text)
        self.assertIn('tools/custom_matrix_gui_recorded.py', text)
        self.assertIn('text="Preferred WT source"', text)
        self.assertIn('tools/dedup_control_gui.py', text)
        self.assertIn('text="Open Processing Logs"', text)
        self.assertNotIn("Image.open", text)
        self.assertNotIn("subprocess.run", text)

    def test_one_plate_proof_uses_selectable_four_point_adapter(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        self.assertIn("run_one_plate_validation as one_plate_validation", text)
        self.assertIn('text="Run one-plate 4-point proof (choose plate)"', text)
        start = text.index("def run_one_plate_validation")
        end = text.index("def standard_output_count", start)
        block = text[start:end]
        self.assertNotIn("one_plate_validation.proof_is_running()", block)
        self.assertIn("filedialog.askopenfilename(", block)
        self.assertIn("filename = Path(chosen).name", block)
        self.assertIn("selected = one_plate_validation.run(filename, legacy=True, rerun_done=rerun_done)", block)
        self.assertIn("authoritative prepare-only results remain available", block)
        self.assertIn("Fiji macro handoff", block)

    def test_controller_exposes_only_canonical_csv_runtime_actions(self) -> None:
        base = (REPO_ROOT / "tools" / "workflow_controller.py").read_text(encoding="utf-8")
        extended = EXTENDED.read_text(encoding="utf-8")
        self.assertIn('text="Reconcile / validate CSV workflow"', base)
        self.assertIn('text="Run one-plate 4-point proof (choose plate)"', extended)
        self.assertIn('text="Reset / re-run selected DONE plate"', extended)
        for retired in (
            "Synthetic test plate",
            "Full-column alignment",
            "Global visibility",
            "Run full-column batch",
            "Run 4-point fallback",
            "Start alignment hotkeys",
            "Stop alignment hotkeys",
        ):
            self.assertNotIn(f'text="{retired}"', base)

    def test_standard_multi_output_jobs_preview_first_by_default_with_opt_out(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        self.assertIn("self.preview_standard_outputs = tk.BooleanVar(value=True)", text)
        self.assertIn("Preview first when a standard Pillow job will create multiple images", text)
        self.assertIn("standard_pillow_preview.build_preview(alias)", text)
        self.assertIn("if count <= 1:", text)
        self.assertIn("self.run_standard_output(alias)", text)
        self.assertIn("Preview rejected. Full Pillow output was not generated.", text)

    def test_deduplicated_dropdown_never_silently_uses_legacy_control_default(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        start = text.index("def run_pillow_job")
        block = text[start:]
        dedup = block.index('if alias == "all-strains-dedup":')
        opt_out = block.index("if not self.preview_standard_outputs.get():")
        self.assertLess(dedup, opt_out)
        self.assertIn('self.launch_python("tools/dedup_control_gui.py")', block[dedup:opt_out])
        self.assertIn("Choose the preferred WT source", block[dedup:opt_out])

    def test_label_individual_count_uses_validated_current_crops(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        start = text.index("def standard_output_count")
        end = text.index("def last_output_text", start)
        block = text[start:end]
        self.assertIn('if alias == "label-individual":', block)
        self.assertIn("validate_unique_crop_matches", block)
        self.assertIn("allow_missing=False", block)

    def test_successful_standard_outputs_get_human_and_machine_records(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        start = text.index("def record_standard_output")
        end = text.index("def run_standard_output", start)
        block = text[start:end]
        self.assertIn("write_output_records(", block)
        self.assertIn("selection=selection", block)
        self.assertIn("required_crops=required", block)
        self.assertIn('display_mode="raw"', block)
        self.assertIn("Processing Log", block)

    def test_processing_logs_button_uses_human_facing_folder_name(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        start = text.index("def open_processing_logs")
        end = text.index("def run_one_plate_validation", start)
        block = text[start:end]
        self.assertIn('Path(raw) / "Processing Logs"', block)
        self.assertNotIn("_workflow", block)

    def test_windows_starter_uses_extended_controller(self) -> None:
        text = STARTER.read_text(encoding="utf-8")
        self.assertIn("tools\\workflow_controller_extended.py", text)
        self.assertNotIn("tools\\workflow_controller.py", text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run_dedup_with_control.py"
GUI = REPO_ROOT / "tools" / "dedup_control_gui.py"


class DedupControlPreviewContractTests(unittest.TestCase):
    def test_preview_uses_same_selected_control_patch_and_top_only_generated_copy(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        start = text.index("def build_preview")
        end = text.index("def run(", start)
        block = text[start:end]
        self.assertIn('configured_copy("all-strains-dedup"', block)
        self.assertIn("patch_preferred_control(configured, experiment.strip(), set_name.strip())", block)
        self.assertIn("patch_first_state(configured)", block)
        self.assertIn("stage_selected_crops", block)
        self.assertIn("normalize_crop_orientation", block)
        self.assertIn("Expected one representative deduplicated preview image", block)

    def test_gui_previews_by_default_and_reject_does_not_run_full_job(self) -> None:
        text = GUI.read_text(encoding="utf-8")
        self.assertIn("self.preview_first = tk.BooleanVar(value=True)", text)
        self.assertIn("Preview Top output before generating Top + Low", text)
        build_at = text.index("def build(self)")
        block = text[build_at:]
        preview_at = block.index("preview = build_preview(exp, set_name)")
        run_at = block.index("output = run(exp, set_name, no_open_output=False)")
        self.assertLess(preview_at, run_at)
        self.assertIn("Preview rejected. Full deduplicated output was not generated.", block[preview_at:run_at])

    def test_successful_dedup_output_records_control_source_and_full_selection(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        run_at = text.index("def run(")
        block = text[run_at:]
        output_check = block.index("if output is None or not pillow_adapter.directory_has_content(output):")
        records = block.index("write_output_records(", output_check)
        self.assertGreater(records, output_check)
        record_block = block[records:block.index("print(", records)]
        self.assertIn('output_type="all strains (deduplicated controls)"', record_block)
        self.assertIn("selection=full_project_selection(config)", record_block)
        self.assertIn('control_source={"experiment": experiment.strip(), "set": set_name.strip()}', record_block)

    def test_gui_surfaces_human_log_but_leaves_machine_recipe_in_backend_area(self) -> None:
        text = GUI.read_text(encoding="utf-8")
        self.assertIn("record_paths", text)
        self.assertIn("Processing Log:\\n{human_log}", text)
        self.assertIn("machine recipe was saved separately under _workflow", text)


if __name__ == "__main__":
    unittest.main()

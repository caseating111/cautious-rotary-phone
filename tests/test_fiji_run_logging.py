from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_four_point_batch_from_config as batch


class FijiRunLoggingTests(unittest.TestCase):
    def test_run_numbers_follow_only_completed_dividers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / batch.ALIGNMENT_LOG_NAME
            log.write_text(
                "===== Batch All | Run 001 | COMPLETED =====\n"
                "an interrupted-looking Run 900 message\n"
                "===== Single | Run 007 | COMPLETED =====\n",
                encoding="utf-8",
            )
            self.assertEqual(batch.next_alignment_run_number(log), 8)

    def test_generated_logging_uses_one_dataset_file_and_no_imagej_print(self) -> None:
        source = batch.SOURCE_MACRO.read_text(encoding="utf-8")
        source = batch.configure_source_settings(
            source,
            {
                "grid_csv": "C:/metadata/grid.csv",
                "image_root": "C:/raw",
                "crop_output": "C:/crops",
                "crop_width": 20,
                "crop_height": 48,
            },
        )
        source = batch.enhance_metadata_lookup(source)
        source = batch.enhance_four_point_macro(source)
        with tempfile.TemporaryDirectory() as temp, patch.object(batch, "APP_DIR", Path(temp) / "app"):
            generated = batch.configure_run_logging(
                source,
                {"matrix_output": str(Path(temp) / "matrices")},
                "Batch Folder",
            )

        self.assertNotIn("print(", generated)
        self.assertIn('runLabel = "Batch Folder";', generated)
        self.assertIn('runSequence = "001";', generated)
        self.assertEqual(generated.count(batch.ALIGNMENT_LOG_NAME), 1)
        self.assertLess(generated.index("completeWorkflowRun("), generated.index('showMessage(\n    "ALL DONE"'))
        self.assertIn('"===== " + runLabel + " | Run " + runSequence + " | COMPLETED =====\\n"', generated)

    def test_all_current_mode_labels_are_accepted(self) -> None:
        minimal = (
            'inputRoot  = "path here";\n'
            "// ============================================================\n// FINISHED\n// ============================================================\n"
            "// ============================================================\n// FUNCTIONS\n// ============================================================\n"
        )
        with tempfile.TemporaryDirectory() as temp, patch.object(batch, "APP_DIR", Path(temp) / "app"):
            config = {"matrix_output": str(Path(temp) / "matrices")}
            for label in ("Batch All", "Batch Folder", "Single", "Single Rerun"):
                with self.subTest(label=label):
                    self.assertIn(f'runLabel = "{label}";', batch.configure_run_logging(minimal, config, label))


if __name__ == "__main__":
    unittest.main()

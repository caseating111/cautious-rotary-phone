from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "existing scripts clean" / "folder per strain all indiv strains labelled.py"


class LabelIndividualOutputTests(unittest.TestCase):
    def test_labelled_individual_job_uses_its_unique_output_folder(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertIn('MATRIX_OUTPUT = make_unique_folder(', text)
        output_at = text.index("output_path = (")
        output_block = text[output_at : text.index(")\n        try:", output_at)]
        self.assertIn("MATRIX_OUTPUT", output_block)
        self.assertNotIn("MATRIX_ROOT", output_block)
        self.assertIn('f"{MATRIX_OUTPUT}"', text)

    def test_labelled_individual_job_declares_no_internal_rotation_for_shared_adapter(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertEqual(text.count("ROTATE_IMAGES_90_CCW = False"), 1)
        self.assertNotIn("ROTATE_IMAGES_90_CCW = True", text)
        self.assertNotIn("def rotate_everything", text)
        self.assertIn("wrapper supplies already-normalized disposable staged inputs", text)


if __name__ == "__main__":
    unittest.main()

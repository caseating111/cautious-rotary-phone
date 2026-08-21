from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "existing scripts clean" / "folder per strain all indiv strains labelled.py"


class LabelIndividualOutputTests(unittest.TestCase):
    def test_labelled_individual_job_uses_its_unique_output_folder(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertIn('MATRIX_OUTPUT = make_unique_folder(', text)
        self.assertIn("output_path = MATRIX_OUTPUT / strain_folder / path.name", text)
        self.assertIn('f"{MATRIX_OUTPUT}"', text)

    def test_labelled_individual_job_declares_no_internal_rotation_for_shared_adapter(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertEqual(text.count("ROTATE_IMAGES_90_CCW = False"), 1)
        self.assertNotIn("ROTATE_IMAGES_90_CCW = True", text)
        self.assertNotIn("def rotate_everything", text)
        self.assertIn("wrapper supplies already-normalized disposable staged inputs", text)

    def test_normal_label_lookup_uses_authoritative_metadata_before_legacy_filename_parser(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        map_at = text.index("exact_labels = read_exact_filename_labels(grid)")
        lookup_at = text.index("strain = exact_labels.get(path.name.lower())", map_at)
        fallback_at = text.index("parsed = parse_crop_filename(path)", lookup_at)
        self.assertLess(map_at, lookup_at)
        self.assertLess(lookup_at, fallback_at)
        self.assertIn("IMAGES_CSV.open(", text)
        self.assertIn("labels[filename.lower()] = strain", text)


if __name__ == "__main__":
    unittest.main()

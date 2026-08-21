from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_one_plate_validation as proof


class OnePlateValidationTests(unittest.TestCase):
    def test_default_uses_first_authoritative_pending_row(self) -> None:
        rows = [
            {"Filename": "plate1.jpg", "Experiment": "E1", "Set": "A", "Type": "YPDA"},
            {"Filename": "plate2.jpg", "Experiment": "E2", "Set": "B", "Type": "SALT"},
        ]
        self.assertIs(proof.choose_pending_row(rows), rows[0])
        self.assertIs(proof.choose_pending_row(rows, "plate2.jpg"), rows[1])

    def test_filename_selection_is_exact_and_ambiguous_or_missing_is_rejected(self) -> None:
        rows = [
            {"Filename": "Plate1.jpg"},
            {"Filename": "plate1.jpg"},
        ]
        self.assertEqual(proof.choose_pending_row(rows, "plate1.jpg")["Filename"], "plate1.jpg")
        with self.assertRaises(SystemExit):
            proof.choose_pending_row(rows, "PLATE1.JPG")

    def test_one_row_csv_preserves_header_and_only_selected_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "proof.csv"
            fields = ["Filename", "Experiment", "Set", "Type"]
            row = {"Filename": "plate2.jpg", "Experiment": "E2", "Set": "B", "Type": "SALT"}
            proof.write_one_row_csv(path, fields, row)
            fieldnames, rows = proof.read_pending_rows(path)
            self.assertEqual(fieldnames, fields)
            self.assertEqual(rows, [row])

    def test_macro_patch_changes_only_pending_metadata_path(self) -> None:
        old = proof.batch.macro_path(proof.batch.PENDING_IMAGES_CSV)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "one.csv"
            source = f'imagesFile = "{old}";\nother = "keep";\n'
            patched = proof.patch_prepared_macro(source, target)
            self.assertNotIn(f'imagesFile = "{old}";', patched)
            self.assertIn(f'imagesFile = "{proof.batch.macro_path(target)}";', patched)
            self.assertIn('other = "keep";', patched)

            with self.assertRaises(SystemExit):
                proof.patch_prepared_macro("other = 1;\n", target)

    def test_running_proof_blocks_second_launch_before_prepare(self) -> None:
        class RunningProcess:
            def poll(self):
                return None

        with patch.object(proof, "_ACTIVE_FIJI_PROCESS", RunningProcess()), patch.object(
            proof, "prepare"
        ) as prepare:
            self.assertTrue(proof.proof_is_running())
            with self.assertRaises(SystemExit) as caught:
                proof.run("plate1.jpg")
            self.assertIn("still running", str(caught.exception))
            prepare.assert_not_called()

    def test_four_point_prepare_uses_legacy_configured_macro(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pending = root / "pending.csv"
            configured = root / "legacy.ijm"
            proof_csv = root / "proof.csv"
            proof_macro = root / "proof.ijm"
            pending.write_text(
                "Filename,Experiment,Set,Type\nplate2.jpg,E2,B,SALT\n",
                encoding="utf-8",
            )
            configured.write_text(
                f'imagesFile = "{proof.batch.macro_path(pending)}";\n',
                encoding="utf-8",
            )
            completed = type("Completed", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

            with patch.object(proof.batch, "PENDING_IMAGES_CSV", pending), patch.object(
                proof.batch, "CONFIGURED_LEGACY_MACRO", configured
            ), patch.object(proof, "PROOF_IMAGES_CSV", proof_csv), patch.object(
                proof, "PROOF_LEGACY_MACRO", proof_macro
            ), patch.object(proof.subprocess, "run", return_value=completed) as run_mock:
                built, selected = proof.prepare("plate2.jpg", legacy=True)

            self.assertEqual(built, proof_macro)
            self.assertEqual(selected["Filename"], "plate2.jpg")
            self.assertIn("--legacy", run_mock.call_args.args[0])
            self.assertIn(proof.batch.macro_path(proof_csv), proof_macro.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

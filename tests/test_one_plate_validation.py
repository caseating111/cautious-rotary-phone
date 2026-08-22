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

    def test_roi_click_adapter_uses_double_clahe_and_finds_custom_tool_slots(self) -> None:
        source = proof.batch.enhance_four_point_macro(proof.batch.SOURCE_MACRO.read_text(encoding="utf-8"))
        patched = proof.patch_roi_click_interaction(source)
        self.assertNotIn("CLICK_ROI = 108", patched)
        self.assertNotIn("makeRectangle(round(viewW / 2 - CLICK_ROI", patched)
        self.assertNotIn('run("Enhance Contrast", "saturated=0.35")', patched)
        self.assertIn('roiBoxW = call("ij.Prefs.get", "rect.width", 108)', patched)
        self.assertIn('roiBoxH = call("ij.Prefs.get", "rect.height", 108)', patched)
        self.assertIn("roiBoxSize = maxOf(roiBoxW, roiBoxH)", patched)
        self.assertIn("claheBlock = round(roiBoxSize * 3.3)", patched)
        self.assertEqual(patched.count('run("Enhance Local Contrast (CLAHE)", claheOptions)'), 2)
        self.assertIn('" histogram=256 maximum=1000 mask=*None* fast_(less_accurate)"', patched)
        self.assertIn('run("Select None")', patched)
        self.assertNotIn('setTool("Rotated Rectangle Click Tool', patched)
        self.assertIn("for (toolCandidate = 15; toolCandidate <= 21; toolCandidate++)", patched)
        self.assertIn("setTool(toolCandidate)", patched)
        self.assertIn('startsWith(IJ.getToolName, "Rotated Rectangle Click Tool")', patched)
        self.assertIn("QC_W = w;", patched)
        self.assertIn("QC_H = h;", patched)
        self.assertIn("Overlay.drawRect(qcX - QC_W / 2", patched)

    def test_selected_plate_window_match_is_exact_and_case_insensitive(self) -> None:
        with patch.object(
            proof,
            "open_window_titles",
            return_value=["Fiji", "other.jpg", "PLATE1.JPG", "plate1.jpg - notes"],
        ):
            self.assertTrue(proof.proof_plate_is_open("plate1.jpg"))
            self.assertFalse(proof.proof_plate_is_open("plate2.jpg"))
            self.assertFalse(proof.proof_plate_is_open("notes"))

    def test_open_selected_plate_blocks_before_prepare_but_other_images_do_not(self) -> None:
        with patch.object(proof, "proof_plate_is_open", return_value=True), patch.object(
            proof, "prepare"
        ) as prepare:
            with self.assertRaises(SystemExit) as caught:
                proof.run("plate1.jpg")
            self.assertIn("selected proof plate is already open", str(caught.exception))
            prepare.assert_not_called()

    def test_live_fiji_process_does_not_block_another_proof(self) -> None:
        class RunningProcess:
            def poll(self):
                return None

        selected = {"Filename": "plate1.jpg"}
        fake_config = {"fiji_executable": str(Path(__file__))}
        launched = object()

        with patch.object(proof, "_ACTIVE_FIJI_PROCESS", RunningProcess()), patch.object(
            proof, "proof_plate_is_open", return_value=False
        ), patch.object(
            proof, "prepare", return_value=(Path("proof.ijm"), selected)
        ) as prepare, patch.object(
            proof.batch, "load_config", return_value=fake_config
        ), patch.object(
            proof.subprocess, "Popen", return_value=launched
        ) as popen:
            self.assertFalse(proof.proof_is_running())
            result = proof.run("plate1.jpg")

        self.assertEqual(result, selected)
        prepare.assert_called_once_with("plate1.jpg", legacy=False)
        popen.assert_called_once()

    def test_new_roi_click_patch_requires_one_restart_before_legacy_proof(self) -> None:
        fake_fiji = Path(__file__)
        fake_config = {"fiji_executable": str(fake_fiji)}
        with patch.object(proof, "proof_plate_is_open", return_value=False), patch.object(
            proof.batch, "load_config", return_value=fake_config
        ), patch.object(proof, "ensure_roi_click_patch", return_value=True), patch.object(
            proof, "prepare"
        ) as prepare:
            with self.assertRaises(SystemExit) as caught:
                proof.run("plate1.jpg", legacy=True)
        self.assertIn("Close/restart Fiji once", str(caught.exception))
        prepare.assert_not_called()

    def test_roi_click_patch_uses_existing_preset_helper_and_refuses_ambiguity(self) -> None:
        fake_fiji = Path(__file__)
        with patch.object(
            proof.roi_preset_gui,
            "find_roi_click_tools",
            return_value=[Path("one.ijm")],
        ), patch.object(
            proof.roi_preset_gui,
            "patch_roi_click_tools",
            return_value=Path("backup.bak"),
        ) as patch_plugin:
            self.assertTrue(proof.ensure_roi_click_patch(fake_fiji))
            patch_plugin.assert_called_once_with(Path("one.ijm"))

        with patch.object(
            proof.roi_preset_gui,
            "find_roi_click_tools",
            return_value=[Path("one.ijm"), Path("two.ijm")],
        ):
            with self.assertRaises(SystemExit):
                proof.ensure_roi_click_patch(fake_fiji)

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
            ), patch.object(proof, "patch_roi_click_interaction", side_effect=lambda text: text), patch.object(
                proof.subprocess, "run", return_value=completed
            ) as run_mock:
                built, selected = proof.prepare("plate2.jpg", legacy=True)

            self.assertEqual(built, proof_macro)
            self.assertEqual(selected["Filename"], "plate2.jpg")
            self.assertIn("--legacy", run_mock.call_args.args[0])
            self.assertIn(proof.batch.macro_path(proof_csv), proof_macro.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import subprocess
import sys
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

    def test_filename_selection_is_case_insensitive_and_ambiguous_or_missing_is_rejected(self) -> None:
        rows = [
            {"Filename": "Plate1.jpg"},
            {"Filename": "plate1.jpg"},
        ]
        with self.assertRaises(SystemExit):
            proof.choose_pending_row(rows, "plate1.jpg")
        self.assertEqual(proof.choose_pending_row([rows[0]], "plate1.JPG")["Filename"], "Plate1.jpg")
        with self.assertRaises(SystemExit):
            proof.choose_pending_row(rows, "missing.jpg")

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
            source = f'imagesFile = "{old}";\nprocessedImages++;\nprint("keep");\n'
            patched = proof.patch_prepared_macro(source, target)
            self.assertNotIn(f'imagesFile = "{old}";', patched)
            self.assertIn(f'imagesFile = "{proof.batch.macro_path(target)}";', patched)
            self.assertIn('processedImages++;\n        exit();', patched)
            self.assertIn('print("keep");', patched)

            with self.assertRaises(SystemExit):
                proof.patch_prepared_macro("other = 1;\n", target)

    def test_four_point_generator_directly_uses_whole_image_double_clahe_and_rotated_qc(self) -> None:
        generated = proof.batch.enhance_four_point_macro(proof.batch.SOURCE_MACRO.read_text(encoding="utf-8"))
        self.assertNotIn("CLICK_ROI = 108", generated)
        self.assertNotIn("makeRectangle(round(viewW / 2 - CLICK_ROI", generated)
        self.assertNotIn('run("Enhance Contrast", "saturated=0.35")', generated)
        self.assertNotIn("sampleW =", generated)
        self.assertNotIn("sampleH =", generated)
        self.assertNotIn("sampleX =", generated)
        self.assertNotIn("sampleY =", generated)
        self.assertIn('run("Select None")', generated)
        self.assertLess(
            generated.index('run("Select None")'),
            generated.index('run("Enhance Local Contrast (CLAHE)", claheOptions)'),
        )
        self.assertIn('roiBoxW = parseFloat(call("ij.Prefs.get", "rect.width", 108))', generated)
        self.assertIn('roiBoxH = parseFloat(call("ij.Prefs.get", "rect.height", 108))', generated)
        self.assertIn("roiBoxSize = maxOf(roiBoxW, roiBoxH)", generated)
        self.assertIn("claheBlock = maxOf(400, round(roiBoxSize * 4))", generated)
        self.assertEqual(generated.count('run("Enhance Local Contrast (CLAHE)", claheOptions)'), 2)
        self.assertIn('" histogram=256 maximum=1000 mask=*None* fast_(less_accurate)"', generated)
        self.assertIn('run("Install...", "install=[" + roiToolsetPath + "]")', generated)
        self.assertNotIn('run("Show All")', generated)
        self.assertIn("for (toolCandidate = 15; toolCandidate <= 21; toolCandidate++)", generated)
        self.assertIn('startsWith(IJ.getToolName, "Rotated Rectangle Click Tool")', generated)
        self.assertIn("gridHX =", generated)
        self.assertIn("gridVX =", generated)
        self.assertIn("hux = gridHX / hLen", generated)
        self.assertIn("vux = gridVX / vLen", generated)
        self.assertIn("Overlay.drawLine(p1x, p1y, p2x, p2y)", generated)
        self.assertIn("p1x = qcX - (QC_W / 2) * hux", generated)
        self.assertIn("Overlay.drawLine(topX, topY, bottomX, bottomY)", generated)
        self.assertNotIn("Overlay.drawRect(qcX", generated)

    def test_production_legacy_macro_uses_the_same_clahe_roi_and_qc_adapter(self) -> None:
        source = proof.batch.SOURCE_MACRO.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp, patch.object(
            proof.batch, "configure_source_settings", return_value=source
        ), patch.object(proof.batch, "APP_DIR", Path(temp)), patch.object(
            proof.batch, "CONFIGURED_LEGACY_MACRO", Path(temp) / "legacy.ijm"
        ):
            exact_path = proof.batch.build_legacy_macro({})
            exact = exact_path.read_text(encoding="utf-8")
        self.assertEqual(exact.count('run("Enhance Local Contrast (CLAHE)", claheOptions)'), 2)
        self.assertIn('" histogram=256 maximum=1000 mask=*None* fast_(less_accurate)"', exact)
        self.assertIn("claheBlock = maxOf(400, round(roiBoxSize * 4))", exact)
        self.assertIn("Overlay.drawLine(p1x, p1y, p2x, p2y)", exact)

    def test_direct_batch_script_context_can_build_legacy_interaction(self) -> None:
        tools_dir = proof.batch.REPO_ROOT / "tools"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import shutil, tempfile\n"
                    "from pathlib import Path\n"
                    "import run_four_point_batch_from_config as batch\n"
                    "target=Path(tempfile.mkdtemp())\n"
                    "source=batch.SOURCE_MACRO.read_text(encoding='utf-8')\n"
                    "batch.configure_source_settings=lambda _source,_config: source\n"
                    "batch.APP_DIR=target\n"
                    "batch.CONFIGURED_LEGACY_MACRO=target/'legacy.ijm'\n"
                    "batch.build_legacy_macro({})\n"
                    "print('DIRECT_SCRIPT_IMPORT_OK')\n"
                    "shutil.rmtree(target)\n"
                ),
            ],
            cwd=tools_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DIRECT_SCRIPT_IMPORT_OK", result.stdout)

    def test_selected_plate_window_match_is_exact_and_case_insensitive(self) -> None:
        with patch.object(
            proof,
            "open_window_titles",
            return_value=["(Fiji Is Just) ImageJ", "other.jpg", "PLATE1.JPG", "plate1.jpg - notes"],
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

    def test_launcher_command_runs_prepared_macro(self) -> None:
        selected = {"Filename": "plate1.jpg"}
        fake_fiji = Path(__file__)
        fake_config = {"fiji_executable": str(fake_fiji)}
        macro = Path("proof.ijm")
        launched = object()
        with patch.object(proof, "proof_plate_is_open", return_value=False), patch.object(
            proof, "prepare", return_value=(macro, selected)
        ), patch.object(
            proof.batch, "load_config", return_value=fake_config
        ), patch.object(proof.subprocess, "Popen", return_value=launched) as popen:
            result = proof.run("plate1.jpg")
        self.assertEqual(result, selected)
        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], [str(fake_fiji), "--no-splash", "-macro", str(macro)])
        self.assertEqual(popen.call_args.kwargs["cwd"], fake_fiji.parent)

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
                f'imagesFile = "{proof.batch.macro_path(pending)}";\nprocessedImages++;\nprint("done");\n',
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


    def test_done_rerun_uses_authoritative_images_row_when_pending_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pending = root / "pending.csv"
            images = root / "images.csv"
            configured = root / "legacy.ijm"
            proof_csv = root / "proof.csv"
            proof_macro = root / "proof.ijm"
            pending.write_text("Filename,Experiment,Set,Type\n", encoding="utf-8")
            images.write_text("Filename,Experiment,Set,Type\nPlate.JPG,E,S,T\n", encoding="utf-8")
            configured.write_text(
                f'imagesFile = "{proof.batch.macro_path(pending)}";\nprocessedImages++;\nprint("done");\n', encoding="utf-8"
            )
            completed = type(
                "Completed", (), {"returncode": 1, "stdout": "All expected crops already exist", "stderr": ""}
            )()
            config = {"images_csv": str(images)}
            with patch.object(proof.batch, "PENDING_IMAGES_CSV", pending), patch.object(
                proof.batch, "CONFIGURED_LEGACY_MACRO", configured
            ), patch.object(proof, "PROOF_IMAGES_CSV", proof_csv), patch.object(
                proof, "PROOF_LEGACY_MACRO", proof_macro
            ), patch.object(proof.subprocess, "run", return_value=completed), patch.object(
                proof, "_prepare_completed_plate_macro", return_value=configured
            ), patch.object(proof.batch, "load_config", return_value=config):
                built, selected = proof.prepare("plate.jpg", legacy=True, rerun_done=True)
        self.assertEqual(built, proof_macro)
        self.assertEqual(selected["Filename"], "Plate.JPG")


if __name__ == "__main__":
    unittest.main()

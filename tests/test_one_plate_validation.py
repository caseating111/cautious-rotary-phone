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
            source = f'imagesFile = "{old}";\nother = "keep";\n'
            patched = proof.patch_prepared_macro(source, target)
            self.assertNotIn(f'imagesFile = "{old}";', patched)
            self.assertIn(f'imagesFile = "{proof.batch.macro_path(target)}";', patched)
            self.assertIn('other = "keep";', patched)

            with self.assertRaises(SystemExit):
                proof.patch_prepared_macro("other = 1;\n", target)

    def test_roi_click_adapter_uses_whole_image_double_clahe_rotated_qc_and_shows_fiji(self) -> None:
        source = proof.batch.enhance_four_point_macro(proof.batch.SOURCE_MACRO.read_text(encoding="utf-8"))
        patched = proof.patch_roi_click_interaction(source)
        self.assertNotIn("CLICK_ROI = 108", patched)
        self.assertNotIn("makeRectangle(round(viewW / 2 - CLICK_ROI", patched)
        self.assertNotIn('run("Enhance Contrast", "saturated=0.35")', patched)
        self.assertNotIn("sampleW =", patched)
        self.assertNotIn("sampleH =", patched)
        self.assertNotIn("sampleX =", patched)
        self.assertNotIn("sampleY =", patched)
        self.assertIn('run("Select None")', patched)
        self.assertLess(
            patched.index('run("Select None")'),
            patched.index('run("Enhance Local Contrast (CLAHE)", claheOptions)'),
        )
        self.assertIn('roiBoxW = parseFloat(call("ij.Prefs.get", "rect.width", 108))', patched)
        self.assertIn('roiBoxH = parseFloat(call("ij.Prefs.get", "rect.height", 108))', patched)
        self.assertIn("roiBoxSize = maxOf(roiBoxW, roiBoxH)", patched)
        self.assertIn("claheBlock = round(roiBoxSize * 3.3)", patched)
        self.assertEqual(patched.count('run("Enhance Local Contrast (CLAHE)", claheOptions)'), 2)
        self.assertIn('" histogram=256 maximum=1000 mask=*None* fast_(less_accurate)"', patched)
        self.assertIn('run("Install...", "install=[" + roiToolsetPath + "]")', patched)
        self.assertNotIn('run("Show All")', patched)
        self.assertIn("for (toolCandidate = 15; toolCandidate <= 21; toolCandidate++)", patched)
        self.assertIn('startsWith(IJ.getToolName, "Rotated Rectangle Click Tool")', patched)
        self.assertIn("gridHX =", patched)
        self.assertIn("gridVX =", patched)
        self.assertIn("hux = gridHX / hLen", patched)
        self.assertIn("vux = gridVX / vLen", patched)
        self.assertIn("Overlay.drawLine(p1x, p1y, p2x, p2y)", patched)
        self.assertNotIn("halfW =", patched)
        self.assertNotIn("halfH =", patched)
        self.assertIn("p1x = qcX - (QC_W / 2) * hux", patched)
        self.assertIn("Overlay.drawLine(topX, topY, bottomX, bottomY)", patched)
        self.assertNotIn("Overlay.drawRect(qcX", patched)

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
        self.assertIn("claheBlock = round(roiBoxSize * 3.3)", exact)
        self.assertIn("Overlay.drawLine(p1x, p1y, p2x, p2y)", exact)

    def test_direct_batch_script_context_can_load_legacy_interaction_adapter(self) -> None:
        tools_dir = proof.batch.REPO_ROOT / "tools"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import shutil, tempfile\n"
                    "from pathlib import Path\n"
                    "import run_full_column_batch_from_config as batch\n"
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

    def test_fiji_main_title_contract_includes_observed_desktop_title(self) -> None:
        self.assertTrue(proof._is_fiji_main_title("(Fiji Is Just) ImageJ"))
        self.assertTrue(proof._is_fiji_main_title("Fiji"))
        self.assertTrue(proof._is_fiji_main_title("ImageJ"))
        self.assertFalse(proof._is_fiji_main_title("plate1.jpg"))

    def test_selected_plate_window_match_is_exact_and_case_insensitive(self) -> None:
        with patch.object(
            proof,
            "open_window_titles",
            return_value=["(Fiji Is Just) ImageJ", "other.jpg", "PLATE1.JPG", "plate1.jpg - notes"],
        ):
            self.assertTrue(proof.fiji_is_open())
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
            proof, "proof_is_running", return_value=False
        ), patch.object(
            proof, "proof_plate_is_open", return_value=False
        ), patch.object(proof, "fiji_is_open", return_value=False), patch.object(
            proof, "prepare", return_value=(Path("proof.ijm"), selected)
        ) as prepare, patch.object(proof, "arm_invocation"), patch.object(
            proof, "source_dispositions", return_value=[]
        ), patch.object(proof, "PROOF_STATUS_FILE", Path(tempfile.gettempdir()) / "proof-test-status.txt"), patch.object(
            proof, "PROOF_LAUNCH_LOG", Path(tempfile.gettempdir()) / "proof-test-launch.log"
        ), patch.object(
            proof.batch, "load_config", return_value=fake_config
        ), patch.object(
            proof.subprocess, "Popen", return_value=launched
        ) as popen, patch.object(proof, "ensure_fiji_main_window_visible", return_value=True) as visible:
            self.assertFalse(proof.proof_is_running())
            result = proof.run("plate1.jpg")

        self.assertEqual(result, selected)
        prepare.assert_called_once_with("plate1.jpg", legacy=False, rerun_done=False)
        visible.assert_called_once_with()
        command = popen.call_args.args[0]
        self.assertIn("--no-splash", command)
        self.assertEqual(command[-2:], ["-macro", str(Path("proof.ijm"))])
        self.assertEqual(popen.call_args.kwargs["cwd"], Path(fake_config["fiji_executable"]).parent)

    def test_existing_fiji_uses_legacy_macro_single_instance_handoff(self) -> None:
        selected = {"Filename": "plate1.jpg"}
        fake_fiji = Path(__file__)
        fake_config = {"fiji_executable": str(fake_fiji)}
        macro = Path("proof.ijm")
        with patch.object(proof, "proof_is_running", return_value=False), patch.object(
            proof, "proof_plate_is_open", return_value=False
        ), patch.object(
            proof, "fiji_is_open", return_value=True
        ), patch.object(proof, "prepare", return_value=(macro, selected)), patch.object(
            proof, "arm_invocation"
        ), patch.object(proof, "source_dispositions", return_value=[]), patch.object(
            proof, "PROOF_STATUS_FILE", Path(tempfile.gettempdir()) / "proof-test-status.txt"
        ), patch.object(proof, "PROOF_LAUNCH_LOG", Path(tempfile.gettempdir()) / "proof-test-launch.log"), patch.object(
            proof, "fiji_macro_command", return_value=(["javaw", "-macro", str(macro)], "ij1-socket-handoff")
        ), patch.object(
            proof.batch, "load_config", return_value=fake_config
        ), patch.object(proof.subprocess, "Popen") as popen, patch.object(
            proof, "ensure_fiji_main_window_visible", return_value=True
        ) as visible:
            result = proof.run("plate1.jpg")
        self.assertEqual(result, selected)
        visible.assert_called_once_with()
        self.assertEqual(
            popen.call_args.args[0],
            ["javaw", "-macro", str(macro)],
        )
        self.assertEqual(popen.call_args.kwargs["cwd"], fake_fiji.parent)

    def test_new_roi_click_patch_requires_one_restart_before_legacy_proof(self) -> None:
        fake_fiji = Path(__file__)
        fake_config = {"fiji_executable": str(fake_fiji)}
        with patch.object(proof, "proof_is_running", return_value=False), patch.object(
            proof, "proof_plate_is_open", return_value=False
        ), patch.object(
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
            ), patch.object(proof.subprocess, "run", return_value=completed) as run_mock:
                built, selected = proof.prepare("plate2.jpg", legacy=True)

            self.assertEqual(built, proof_macro)
            self.assertEqual(selected["Filename"], "plate2.jpg")
            self.assertIn("--legacy", run_mock.call_args.args[0])
            self.assertIn(proof.batch.macro_path(proof_csv), proof_macro.read_text(encoding="utf-8"))

    def test_invocation_guard_claims_once_and_marks_success(self) -> None:
        source = "gridText = File.openAsString(gridFile);\n// ============================================================\n// FINISHED\n// ============================================================\n"
        with patch.object(proof, "PROOF_STATUS_FILE", Path("C:/proof.status")):
            guarded = proof.patch_invocation_guard(source, "abc")
        self.assertIn('proofStatus != "READY " + proofToken', guarded)
        self.assertIn('File.saveString("RUNNING " + proofToken', guarded)
        self.assertIn('File.saveString("DONE abc"', guarded)

    def test_existing_fiji_command_bypasses_fiji_launcher_for_ij1_socket_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fiji = root / "fiji-windows-x64.exe"
            jar = root / "jars" / "ij-1.54p.jar"
            javaw = root / "java" / "win64" / "jdk" / "bin" / "javaw.exe"
            jar.parent.mkdir(parents=True)
            javaw.parent.mkdir(parents=True)
            jar.touch()
            javaw.touch()
            command, route = proof.fiji_macro_command(fiji, Path("proof.ijm"), existing_fiji=True)
        self.assertEqual(route, "ij1-socket-handoff")
        self.assertEqual(command[0], str(javaw))
        self.assertIn("ij.ImageJ", command)
        self.assertNotIn(str(fiji), command)

    def test_source_dispositions_cover_each_physical_file_with_casefolded_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            images = root / "images.csv"
            pending = root / "pending.csv"
            folder = root / "EXP1"
            folder.mkdir()
            for name in ("active.JPG", "waiting.jpg", "done.jpg", "unknown.tif"):
                (folder / name).touch()
            images.write_text(
                "Filename,Experiment,Set,Type\nACTIVE.jpg,E,S,T\nwaiting.JPG,E,S,T\ndone.jpg,E,S,T\n",
                encoding="utf-8",
            )
            pending.write_text(
                "Filename,Experiment,Set,Type\nwaiting.jpg,E,S,T\n",
                encoding="utf-8",
            )
            with patch.object(proof.batch, "PENDING_IMAGES_CSV", pending):
                decisions = proof.source_dispositions(
                    {"images_csv": str(images), "image_root": str(root)}, "active.jpg"
                )
        self.assertEqual(
            decisions,
            [
                "ACTIVE: EXP1/active.JPG",
                "DONE: EXP1/done.jpg",
                "NOT_LISTED: EXP1/unknown.tif",
                "PENDING: EXP1/waiting.jpg",
            ],
        )

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
                f'imagesFile = "{proof.batch.macro_path(pending)}";\n', encoding="utf-8"
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

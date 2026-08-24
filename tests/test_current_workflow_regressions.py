from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_four_point_batch_from_config as batch
from tools import workflow_controller_extended as controller


REPO_ROOT = Path(__file__).resolve().parents[1]


class _FinishedProcess:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.pid = 12345

    def poll(self):
        return self.returncode

    def wait(self):
        return self.returncode


class CurrentWorkflowRegressionTests(unittest.TestCase):
    def test_windows_liveness_probe_does_not_terminate_live_process(self) -> None:
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
        try:
            self.assertTrue(controller.process_is_running(child.pid))
            self.assertIsNone(child.poll(), "liveness check must not terminate the child on Windows")
        finally:
            child.terminate()
            child.wait(timeout=5)


    def test_stale_owned_fiji_cleanup_terminates_only_recorded_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pid_file = Path(temp) / "owned.txt"
            pid_file.write_text("123\ninvalid\n456\n-2\n", encoding="utf-8")
            with patch.object(controller, "OWNED_FIJI_PIDS_FILE", pid_file), patch.object(
                controller, "terminate_owned_fiji"
            ) as terminate:
                controller.cleanup_stale_owned_fiji_processes()

            self.assertEqual({call.args[0] for call in terminate.call_args_list}, {123, 456})
            self.assertFalse(pid_file.exists())

    def test_generated_four_point_bounds_precede_archive_and_export_with_or_without_qc(self) -> None:
        source = batch.SOURCE_MACRO.read_text(encoding="utf-8")
        generated = batch.enhance_four_point_macro(source)
        bounds = generated.index("requireCropFits(")
        archive = generated.index("archiveReplacementCrops(", bounds)
        export = generated.index("// EXPORT CROPS", archive)
        self.assertLess(bounds, archive)
        self.assertLess(archive, export)
        self.assertIn("if (batchGridQC)", generated)
        self.assertIn("} else {\n                accepted = 1;", generated)
        self.assertIn('ACCEPT: Export crops.', generated)
        self.assertNotIn("save grid coordinates", generated.casefold())

    def test_fiji_wrapper_fails_closed_without_completion_sentinel(self) -> None:
        for returncode in (0, 7):
            with self.subTest(returncode=returncode), tempfile.TemporaryDirectory() as temp:
                session = Path(temp) / "state.txt"
                with patch.object(batch.subprocess, "Popen", return_value=_FinishedProcess(returncode)), patch.object(
                    batch, "remember_owned_fiji_process"
                ), patch.object(batch, "control_request", return_value=""):
                    with self.assertRaises(SystemExit):
                        batch.run_fiji_batch(Path("Fiji.exe"), Path("macro.ijm"), session)

    def test_fiji_cancel_is_clean_not_false_success(self) -> None:
        process = _FinishedProcess(0)
        process.poll = unittest.mock.Mock(side_effect=[None, 0])
        with tempfile.TemporaryDirectory() as temp, patch.object(
            batch.subprocess, "Popen", return_value=process
        ), patch.object(batch, "remember_owned_fiji_process"), patch.object(
            batch, "control_request", side_effect=["cancel", "cancel"]
        ), patch.object(batch, "kill_process_tree"):
            batch.run_fiji_batch(Path("Fiji.exe"), Path("macro.ijm"), Path(temp) / "state.txt")

    def test_ahk_hooks_only_fiji_and_preserves_proven_window_hotfixes(self) -> None:
        text = (REPO_ROOT / "ahk" / "four_point_alignment_hotkeys.ah2").read_text(encoding="utf-8")
        self.assertIn('WinGetList("ahk_class SunAwtFrame ahk_exe fiji-windows-x64.exe")', text)
        self.assertNotIn('WinGetList("ahk_class SunAwtFrame")', text)
        self.assertNotIn("for hwnd in WinGetList()\n", text)
        shell = text[text.index("ShellMessage("):text.index("; Position an already-visible Fiji toolbar")]
        gate = 'WinExist("ahk_id " lParam " ahk_exe fiji-windows-x64.exe")'
        self.assertIn(gate, shell)
        self.assertLess(shell.index(gate), shell.index("StartWorkflowWindowWatch()"))
        for preserved in (
            'WinSetAlwaysOnTop(0, "ahk_id " hwnd)',
            'WinMoveBottom("ahk_id " hwnd)',
            "DuplicatePromptDeadline := A_TickCount + 1800",
            "WinHide(",
            "WinClose(",
            'WriteBatchControl("restart")',
        ):
            self.assertIn(preserved, text)

    def test_windows_launchers_probe_exact_runtime_and_private_wrapper_fails_closed(self) -> None:
        controller_text = (REPO_ROOT / "start_controller.cmd").read_text(encoding="utf-8")
        custom_text = (REPO_ROOT / "start_custom_matrix.cmd").read_text(encoding="utf-8")
        probe = "sys.version_info[:2] != (3, 11)"
        for text in (controller_text, custom_text):
            self.assertIn(r"%USERPROFILE%\miniforge3\envs\workflow-c\python.exe", text)
            self.assertIn(r"%USERPROFILE%\.conda\envs\workflow-c\python.exe", text)
            self.assertLess(text.index(r"%USERPROFILE%\miniforge3"), text.index(r"%USERPROFILE%\.conda"))
            self.assertIn(probe, text)
            self.assertIn("import PIL, tkinter, sys", text)
            self.assertIn("call conda", text)
        self.assertLess(controller_text.index('del /q "%CLOSE_REQUEST%"'), controller_text.index(":run_direct"))

        private = (REPO_ROOT / "start_controller_private_test.cmd").read_text(encoding="utf-8")
        self.assertIn("ImageJ-win64.exe", private)
        self.assertIn("fiji-windows-x64.exe", private)
        self.assertIn(":private_dir_failed", private)
        self.assertIn("exit /b 3", private)


if __name__ == "__main__":
    unittest.main()

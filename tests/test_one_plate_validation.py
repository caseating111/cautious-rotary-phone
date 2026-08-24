from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools import run_one_plate_validation as proof


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".local-test-telemetry" / "tmp"


def local_tempdir():
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT)


class OnePlateValidationTests(unittest.TestCase):
    def test_pending_tsv_is_read_with_explicit_tab_delimiter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pending.tsv"
            path.write_text(
                "Folder\tFilename\tExperiment\tSet\tType\nA\tplate.jpg\tE\tS\tT\n",
                encoding="utf-8",
            )
            fields, rows = proof.read_pending_rows(path, delimiter="\t")
        self.assertEqual(fields, ["Folder", "Filename", "Experiment", "Set", "Type"])
        self.assertEqual(rows[0]["Filename"], "plate.jpg")

    def test_write_one_row_tsv_preserves_fiji_handoff_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "proof.tsv"
            proof.write_one_row_tsv(
                path,
                {"Folder": "A", "Filename": "plate.jpg", "Experiment": "E", "Set": "S", "Type": "T"},
            )
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(rows, [{"Folder": "A", "Filename": "plate.jpg", "Experiment": "E", "Set": "S", "Type": "T"}])

    def _prepare_with_mocks(self, root: Path, *, rerun_done: bool, replace_existing: bool):
        configured = root / "configured.ijm"
        configured.write_text("configured", encoding="utf-8")
        proof_macro = root / "proof.ijm"
        proof_tsv = root / "proof.tsv"
        manifest = root / "replacement.tsv"
        pending = root / "pending.tsv"
        images_csv = root / "images.csv"
        source = root / "FolderA" / "plate.jpg"
        source.parent.mkdir()
        source.write_bytes(b"synthetic-not-an-image")
        pending_row = {"Folder": "FolderA", "Filename": "plate.jpg", "Experiment": "E", "Set": "S", "Type": "T"}
        authoritative_row = {"Filename": "plate.jpg", "Experiment": "E", "Set": "S", "Type": "T"}
        completed = subprocess.CompletedProcess([], 0, "", "")
        config = {"image_root": str(root), "images_csv": str(images_csv)}

        def read_rows(path: Path, *, delimiter: str = ","):
            if path == pending:
                self.assertEqual(delimiter, "\t")
                return list(pending_row), [pending_row]
            if path == images_csv:
                self.assertEqual(delimiter, ",")
                return list(authoritative_row), [authoritative_row]
            raise AssertionError(f"unexpected metadata path: {path}")

        with patch.object(proof.batch, "PENDING_IMAGES_TSV", pending), patch.object(
            proof.batch, "CONFIGURED_FOUR_POINT_MACRO", configured
        ), patch.object(proof, "FOUR_POINT_PLATE_MACRO", proof_macro), patch.object(
            proof, "PROOF_IMAGES_TSV", proof_tsv
        ), patch.object(proof, "REPLACEMENT_MANIFEST", manifest), patch.object(
            proof.subprocess, "run", return_value=completed
        ), patch.object(proof, "read_pending_rows", side_effect=read_rows) as read_mock, patch.object(
            proof.batch, "load_config", return_value=config
        ), patch.object(proof, "_prepare_completed_plate_macro", return_value=configured) as completed_macro, patch.object(
            proof.preflight_batch, "discover_sources", return_value=[source]
        ), patch.object(proof, "patch_prepared_macro", return_value="patched"), patch.object(
            proof.crop_replacement_manifest, "write_manifest"
        ) as write_manifest:
            result = proof.prepare(
                "plate.jpg",
                rerun_done=rerun_done,
                replace_existing=replace_existing,
            )
        return result, read_mock, completed_macro, write_manifest, manifest, proof_tsv

    def test_ordinary_single_remains_pending_only_when_replacement_is_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result, read_mock, completed_macro, write_manifest, manifest, proof_tsv = self._prepare_with_mocks(
                Path(temp), rerun_done=False, replace_existing=True
            )
        self.assertEqual(result[1]["Filename"], "plate.jpg")
        self.assertEqual(read_mock.call_count, 1)
        completed_macro.assert_not_called()
        write_manifest.assert_called_once()
        self.assertTrue(proof_tsv.name.endswith(".tsv"))
        self.assertEqual(manifest.name, "replacement.tsv")

    def test_rerun_uses_authoritative_csv_and_forces_replacement_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result, read_mock, completed_macro, write_manifest, _manifest, _proof_tsv = self._prepare_with_mocks(
                Path(temp), rerun_done=True, replace_existing=False
            )
        self.assertEqual(result[1]["Filename"], "plate.jpg")
        self.assertEqual(read_mock.call_count, 1)
        completed_macro.assert_called_once()
        write_manifest.assert_called_once()

    def test_patch_prepared_macro_scopes_folder_and_replacement_manifest(self) -> None:
        pending = proof.batch.macro_path(proof.batch.PENDING_IMAGES_TSV)
        source = (
            f'imagesFile = "{pending}";\n'
            'folders = getFileList(inputRoot);\n'
            'replacementManifest = "";\n'
            'runLabel = "Batch All";\n'
            'processedImages++;\n        print("done");\n'
        )
        patched = proof.patch_prepared_macro(
            source,
            Path("C:/proof.tsv"),
            Path("C:/replace.tsv"),
            "FolderA",
            "Single Rerun",
        )
        self.assertIn('imagesFile = "C:/proof.tsv";', patched)
        self.assertIn('folders = newArray("FolderA/");', patched)
        self.assertIn('replacementManifest = "C:/replace.tsv";', patched)
        self.assertIn('runLabel = "Single Rerun";', patched)

    def test_run_with_process_launches_grid_finalizer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fiji = root / "ImageJ-win64.exe"
            fiji.write_bytes(b"")
            macro = root / "proof.ijm"
            macro.write_text("macro", encoding="utf-8")
            control = root / "control.request"
            handoff = root / "grid.tsv"
            log = root / "finalizer.log"
            assets = root / "assets"
            config = {"fiji_executable": str(fiji), "images_csv": str(root / "images.csv")}
            fiji_process = MagicMock(pid=123)
            finalizer_process = MagicMock(pid=456)
            with patch.object(proof.batch, "ACTIVE_BATCH_FILE", root / "inactive"), patch.object(
                proof.batch, "CONTROL_REQUEST_FILE", control
            ), patch.object(proof.batch, "GRID_COORDINATE_HANDOFF", handoff), patch.object(
                proof, "GRID_FINALIZER_LOG", log
            ), patch.object(proof.batch, "load_config", return_value=config), patch.object(
                proof, "ensure_roi_click_patch", return_value=False
            ), patch.object(
                proof, "prepare", return_value=(macro, {"Filename": "plate.jpg"})
            ), patch.object(
                proof.batch, "grid_coordinate_asset_directory", return_value=assets
            ), patch.object(
                proof.subprocess, "Popen", side_effect=[fiji_process, finalizer_process]
            ) as popen:
                selected, process = proof.run_with_process()
        self.assertEqual(selected["Filename"], "plate.jpg")
        self.assertIs(process, fiji_process)
        self.assertEqual(popen.call_count, 2)
        finalizer_command = popen.call_args_list[1].args[0]
        self.assertEqual(Path(finalizer_command[1]), proof.GRID_FINALIZER)
        self.assertEqual(Path(finalizer_command[2]), handoff)
        self.assertEqual(Path(finalizer_command[3]), assets)

if __name__ == "__main__":
    unittest.main()

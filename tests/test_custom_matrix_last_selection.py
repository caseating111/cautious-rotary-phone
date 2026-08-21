from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import custom_matrix_selection as custom


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_RUNNER = REPO_ROOT / "tools" / "custom_matrix_selection.py"
PRESENTATION_RUNNER = REPO_ROOT / "tools" / "run_custom_matrix_presentation.py"


class CustomMatrixLastSelectionTests(unittest.TestCase):
    def selection(self) -> dict:
        return {
            "groups": [{"experiment": "E2", "set": "A", "columns": [1, 3]}],
            "conditions": ["YPDA"],
            "states": ["Top"],
        }

    def test_save_helper_writes_normalized_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "last.json"
            with patch.object(custom, "APP_DIR", root), patch.object(custom, "LAST_SELECTION_FILE", path):
                custom.save_last_selection(self.selection())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), custom.normalize_selection(self.selection()))

    def test_raw_route_remembers_selection_only_after_valid_nonempty_output(self) -> None:
        text = RAW_RUNNER.read_text(encoding="utf-8")
        output_check = text.index('if output is None or not pillow_adapter.directory_has_content(output):')
        remember = text.index("save_last_selection(selection)", output_check)
        self.assertGreater(remember, output_check)
        self.assertNotIn("LAST_SELECTION_FILE.write_text", text[text.index("def run_selection"):output_check])

    def test_presentation_route_remembers_successful_selection_too(self) -> None:
        text = PRESENTATION_RUNNER.read_text(encoding="utf-8")
        output_check = text.index('if output is None or not pillow_adapter.directory_has_content(output):')
        remember = text.index("custom.save_last_selection(selection)", output_check)
        self.assertGreater(remember, output_check)


if __name__ == "__main__":
    unittest.main()

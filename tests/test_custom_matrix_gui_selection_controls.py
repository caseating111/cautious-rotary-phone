from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUI = REPO_ROOT / "tools" / "custom_matrix_gui.py"


class CustomMatrixGuiSelectionControlTests(unittest.TestCase):
    def test_group_shortcut_keeps_condition_and_state_choices_independent(self) -> None:
        text = GUI.read_text(encoding="utf-8")
        start = text.index("def select_only_group")
        end = text.index("def set_conditions", start)
        block = text[start:end]

        self.assertIn("group_key == key", block)
        self.assertNotIn("self.set_conditions", block)
        self.assertNotIn("self.state_vars", block)
        self.assertIn("conditions and Top/Low were left unchanged", block)

    def test_condition_all_none_controls_do_not_reset_strains_or_states(self) -> None:
        text = GUI.read_text(encoding="utf-8")
        self.assertIn('text="Only this set"', text)
        self.assertIn("command=lambda: self.set_conditions(True)", text)
        self.assertIn("command=lambda: self.set_conditions(False)", text)

        start = text.index("def set_conditions")
        end = text.index("def set_all", start)
        block = text[start:end]
        self.assertIn("self.condition_vars.values()", block)
        self.assertNotIn("self.group_vars", block)
        self.assertNotIn("self.state_vars", block)


if __name__ == "__main__":
    unittest.main()

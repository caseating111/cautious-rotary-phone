from __future__ import annotations

import unittest

from tools.custom_matrix_gui import validate_selection_available


class CustomMatrixSelectionRestoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.groups = {
            ("E1", "A"): [(1, "WT"), (2, "mut1")],
            ("E2", "B"): [(1, "WT"), (3, "mut2")],
        }
        self.conditions = ["YPDA", "SALT"]

    def test_exact_available_selection_is_preserved(self) -> None:
        selection = {
            "groups": [{"experiment": "e1", "set": "a", "columns": [2]}],
            "conditions": ["salt"],
            "states": ["low"],
        }
        clean = validate_selection_available(selection, self.groups, self.conditions)
        self.assertEqual(clean["groups"], [{"experiment": "e1", "set": "a", "columns": [2]}])
        self.assertEqual(clean["conditions"], ["salt"])
        self.assertEqual(clean["states"], ["Low"])

    def test_removed_group_is_rejected_instead_of_silently_dropped(self) -> None:
        selection = {
            "groups": [{"experiment": "E9", "set": "Z", "columns": [1]}],
            "conditions": ["YPDA"],
            "states": ["Top"],
        }
        with self.assertRaises(SystemExit) as caught:
            validate_selection_available(selection, self.groups, self.conditions)
        self.assertIn("group E9/Z", str(caught.exception))

    def test_removed_column_and_condition_are_both_reported(self) -> None:
        selection = {
            "groups": [{"experiment": "E1", "set": "A", "columns": [2, 99]}],
            "conditions": ["YPDA", "MISSING"],
            "states": ["Top", "Low"],
        }
        with self.assertRaises(SystemExit) as caught:
            validate_selection_available(selection, self.groups, self.conditions)
        text = str(caught.exception)
        self.assertIn("E1/A column 99", text)
        self.assertIn("condition/type MISSING", text)
        self.assertIn("was not applied", text)


if __name__ == "__main__":
    unittest.main()

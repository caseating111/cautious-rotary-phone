from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.run_dedup_with_control import canonical_control, control_groups, patch_preferred_control, validate_control_source


class DeduplicatedControlSourceTests(unittest.TestCase):
    def test_control_groups_are_derived_from_existing_grid_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            grid = root / "grid.csv"
            grid.write_text(
                "Experiment,Set,GridCols,Column,Strain\n"
                "E1,S0,3,1,WT X\n"
                "E1,S0,3,2,mut1\n"
                "E2,A,3,1,WT-X\n"
                "E2,A,3,2,WT Y\n",
                encoding="utf-8",
            )
            groups = control_groups(grid)
            self.assertEqual(groups[("E1", "S0")], {"WT X"})
            self.assertEqual(groups[("E2", "A")], {"WT X", "WT Y"})
            self.assertEqual(canonical_control("wt-y"), "WT Y")

    def test_unknown_control_group_is_rejected_with_available_choices(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            grid = root / "grid.csv"
            grid.write_text(
                "Experiment,Set,GridCols,Column,Strain\nE2,A,2,1,WT X\nE2,A,2,2,WT Y\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit) as caught:
                validate_control_source({"grid_csv": str(grid)}, "E9", "Z")
            self.assertIn("E2/A", str(caught.exception))

    def test_generated_copy_changes_only_preferred_group_condition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "configured.py"
            script.write_text(
                'before\n            if (\n                row["experiment"] == "E2"\n                and row["set"] == "A"\n            ):\nafter\n',
                encoding="utf-8",
            )
            patch_preferred_control(script, "E1", "S0")
            text = script.read_text(encoding="utf-8")
            self.assertIn('row["experiment"] == \'E1\'', text)
            self.assertIn('row["set"] == \'S0\'', text)
            self.assertNotIn('row["experiment"] == "E2"', text)


if __name__ == "__main__":
    unittest.main()

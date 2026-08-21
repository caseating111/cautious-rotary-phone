from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.output_processing_records import write_output_records


class OutputProcessingRecordTests(unittest.TestCase):
    def test_human_log_and_machine_recipe_use_separate_clear_folders(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "EXP_3"
            output.mkdir()
            selection = {
                "groups": [{"experiment": "E2", "set": "A", "columns": [1, 3]}],
                "conditions": ["YPDA", "SALT"],
                "states": ["Top"],
            }
            human, machine = write_output_records(
                root,
                output,
                output_type="custom matrix",
                selection=selection,
                required_crops=4,
                available_crops=4,
                used_crops=4,
                display_mode="raw",
                control_source={"experiment": "E2", "set": "A"},
            )

            self.assertEqual(human.parent.name, "Processing Logs")
            self.assertEqual(machine.parent.name, "output-recipes")
            self.assertEqual(machine.parent.parent.name, "_workflow")
            self.assertEqual(human.stem, machine.stem)

            text = human.read_text(encoding="utf-8")
            self.assertIn("OUTPUT PROCESSING LOG", text)
            self.assertIn("E2 / A: columns 1, 3", text)
            self.assertIn("Conditions/types: YPDA, SALT", text)
            self.assertIn("Required: 4", text)

            recipe = json.loads(machine.read_text(encoding="utf-8"))
            self.assertEqual(recipe["selection"], selection)
            self.assertEqual(recipe["crops"], {"required": 4, "available": 4, "used": 4})
            self.assertEqual(recipe["control_source"], {"experiment": "E2", "set": "A"})


if __name__ == "__main__":
    unittest.main()

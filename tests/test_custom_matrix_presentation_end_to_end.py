from __future__ import annotations

import unittest

from tools import run_custom_matrix_presentation as presentation_job


class CustomMatrixPresentationRetirementTests(unittest.TestCase):
    def test_presentation_job_fails_explicitly_without_writing(self) -> None:
        selection = {
            "groups": [{"experiment": "E2", "set": "A", "columns": [1]}],
            "conditions": ["YPDA"],
            "states": ["Top"],
        }
        with self.assertRaises(SystemExit) as caught:
            presentation_job.run_job(selection, no_open_output=True)
        message = str(caught.exception).casefold()
        self.assertIn("retired", message)
        self.assertIn("raw", message)
        self.assertIn("four-point", message)


if __name__ == "__main__":
    unittest.main()

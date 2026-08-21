from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.finalize_images_reconciliation import validate_review_source_set


class MetadataReviewSourceSetTests(unittest.TestCase):
    def make_sources(self, root: Path, names: list[tuple[str, str]]) -> Path:
        image_root = root / "images"
        for folder, filename in names:
            path = image_root / folder
            path.mkdir(parents=True, exist_ok=True)
            (path / filename).write_bytes(b"placeholder")
        return image_root

    def review(self, names: list[tuple[str, str]]) -> list[dict[str, str]]:
        return [
            {
                "Folder": folder,
                "Filename": filename,
                "Experiment": "E1",
                "Set": "A",
                "Type": "YPDA",
                "Status": "EXISTING",
            }
            for folder, filename in names
        ]

    def test_matching_review_source_set_is_accepted_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            names = [("setA", "plate1.jpg"), ("setB", "plate2.png")]
            image_root = self.make_sources(root, names)
            review = self.review(names)
            validate_review_source_set(review, image_root)

    def test_new_source_after_review_blocks_finalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_root = self.make_sources(
                root,
                [("setA", "plate1.jpg"), ("setA", "plate2.jpg")],
            )
            review = self.review([("setA", "plate1.jpg")])
            with self.assertRaises(SystemExit) as caught:
                validate_review_source_set(review, image_root)
            message = str(caught.exception)
            self.assertIn("review is stale", message)
            self.assertIn("setA/plate2.jpg", message)

    def test_removed_source_after_review_blocks_finalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_root = self.make_sources(root, [("setA", "plate1.jpg")])
            review = self.review(
                [("setA", "plate1.jpg"), ("setB", "old_plate.jpg")]
            )
            with self.assertRaises(SystemExit) as caught:
                validate_review_source_set(review, image_root)
            message = str(caught.exception)
            self.assertIn("Review rows whose source file is no longer present", message)
            self.assertIn("setB/old_plate.jpg", message)


if __name__ == "__main__":
    unittest.main()

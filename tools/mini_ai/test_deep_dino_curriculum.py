"""Offline provenance, split and production-isolation gates for deep DINO."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from deep_dino_curriculum import VIEWS, ingest, verified_views
from deep_dino_student import check_splits, validated_rows
from test_zero_to_cad import manifest
from test_zero_to_cad_visual import features


def fixtures(count: int, split: str):
    doc = manifest(count, split)
    doc["dataset_revision"] = "a" * 40
    doc["teacher_views"] = list(VIEWS)
    for row in doc["records"]:
        row["view_sha256"] = {
            view: hashlib.sha256((row["source_id"] + view).encode()).hexdigest()
            for view in VIEWS}
    teacher = features(doc)
    teacher["dataset_revision"] = "a" * 40
    teacher["view_count"] = len(VIEWS)
    for item in teacher["records"]:
        item["view_count"] = len(VIEWS)
    return doc, teacher


class DeepDinoCurriculumSafety(unittest.TestCase):
    def test_teacher_does_not_require_faces_as_an_input(self):
        doc, teacher = fixtures(35, "train")
        rows = validated_rows(doc, teacher, "train")
        self.assertEqual(len(rows), 35)
        self.assertTrue(all(row["x"][-1] == 0 for row in rows))
        self.assertTrue(all(len(row["y"]) == 24 for row in rows))

    def test_rejects_mismatched_teacher_revision_and_views(self):
        doc, teacher = fixtures(35, "train")
        teacher["dataset_revision"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "Mismatched"):
            validated_rows(doc, teacher, "train")
        doc, teacher = fixtures(35, "train")
        teacher["records"][0]["view_count"] = 2
        with self.assertRaisesRegex(ValueError, "four-view"):
            validated_rows(doc, teacher, "train")

    def test_rejects_leaked_official_source_hash(self):
        doc, t = fixtures(220, "train")
        heldout_doc, v = fixtures(65, "validation")
        a = validated_rows(doc, t, "train")
        b = validated_rows(heldout_doc, v, "validation")
        check_splits(a, b)
        b[0]["hash"] = a[0]["hash"]
        with self.assertRaisesRegex(ValueError, "leaked"):
            check_splits(a, b)

    def test_rejects_underpowered_or_duplicate_training(self):
        doc, teacher = fixtures(35, "train")
        rows = validated_rows(doc, teacher, "train")
        with self.assertRaisesRegex(ValueError, "deep enough"):
            check_splits(rows, rows[:])
        doc, teacher = fixtures(220, "train")
        rows = validated_rows(doc, teacher, "train")
        v, tf = fixtures(65, "validation")
        heldout = validated_rows(v, tf, "validation")
        rows.append(rows[0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            check_splits(rows, heldout)

    def test_hashed_four_view_images_cannot_be_swapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc, _ = fixtures(1, "train")
            row = doc["records"][0]
            row["view_files"] = {}
            row["view_sha256"] = {}
            for view in VIEWS:
                path = root / (row["source_id"] + "__" + view + ".png")
                path.write_bytes(view.encode())
                row["view_files"][view] = path.name
                row["view_sha256"][view] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(len(list(verified_views(doc, root))[0][1]), 4)
            (root / row["view_files"][VIEWS[0]]).write_bytes(b"tamper")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                list(verified_views(doc, root))

    def test_bounded_pinned_source_only_and_no_network_on_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "Freeze source"):
                ingest("train", "latest", offset=0, count=100, scan_limit=500,
                       images=root, output=root / "result.json")
            with self.assertRaisesRegex(ValueError, "Unbounded"):
                ingest("train", "a" * 40, offset=5000, count=2000, scan_limit=9000,
                       images=root, output=root / "result.json")


if __name__ == "__main__":
    unittest.main()

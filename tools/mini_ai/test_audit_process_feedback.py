"""Synthetic fixtures: do not include users' exported prompts in the public repository."""
import json
from pathlib import Path
import tempfile
import unittest
from audit_process_feedback import review_example, requested_drive_count, audit_file


class ProcessReviewTests(unittest.TestCase):
    def test_count_language_variants(self):
        self.assertEqual(requested_drive_count("hover racer with three engines"), 3)
        self.assertEqual(requested_drive_count("hover racer with 3 rear thrusters"), 3)
        self.assertEqual(requested_drive_count("hover SUV with triple boosters"), 3)
        self.assertEqual(requested_drive_count("hover coupe with engines x3"), 3)
        self.assertEqual(requested_drive_count("hover racer with twin engines"), 2)
        self.assertIsNone(requested_drive_count("fast hover racer"))

    def test_detects_mismatch_and_accepts_corrected_recipe(self):
        example = {
            "schema": "assetwright-approved-example-v1",
            "prompt": "hover coupe with triple rear engines",
            "construction_recipe": {
                "operation_sequence": [
                    {"operation": "attach_rear_drive",
                     "parameters": {"housings": 2}}
                ]
            }
        }
        bad = review_example(example)
        self.assertEqual(bad["status"], "mismatch")
        self.assertEqual(bad["issues"][0]["requested_count"], 3)
        example["construction_recipe"]["operation_sequence"][0]["parameters"]["housings"] = 3
        self.assertEqual(review_example(example)["status"], "no_detected_count_mismatch")

    def test_jsonl_input_is_not_modified(self):
        example = {
            "schema": "assetwright-approved-example-v1",
            "prompt": "hover SUV with one engine",
            "construction_recipe": {
                "operation_sequence": [
                    {"operation": "attach_rear_drive",
                     "parameters": {"housings": 2}}
                ]
            }
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "approved.jsonl"
            path.write_text(json.dumps(example) + "\n", encoding="utf-8")
            before = path.read_bytes()
            result = audit_file(path)
            self.assertEqual(result["examples_reviewed"], 1)
            self.assertEqual(result["mismatches"], 1)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

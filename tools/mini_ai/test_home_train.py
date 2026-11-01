"""Offline quality-gate tests; no Blender, GPU or network required."""
import json
from pathlib import Path
import tempfile
import unittest

from home_train import validate, predict, train_once, SEED


class HomeTrainingTests(unittest.TestCase):
    def test_reject_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            validate({"prompt": "hover racer", "length": float("nan")})

    def test_exact_approved_prompt_wins(self):
        examples = [dict(prompt="wide hover suv", length=6.2, width=2.9,
                         roofHeight=1.7, canopyLength=2.3,
                         noseTaper=0.44, rearHaunch=1.2)]
        result = predict("Wide hover SUV", examples)
        self.assertEqual(result["width"], 2.9)

    def test_export_to_candidate_and_report(self):
        example = json.loads(SEED.read_text(encoding="utf-8"))[1]
        record = dict(example, schema="assetwright-approved-example-v1",
                      approved_by_user=True, origin="android-corrected-vehicle")
        with tempfile.TemporaryDirectory() as d:
            inbox = Path(d) / "inbox"
            out = Path(d) / "trained"
            inbox.mkdir()
            (inbox / "approved.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
            report = train_once(inbox, out)
            self.assertIn(report["status"], ("promoted", "rejected_regression"))
            self.assertTrue((out / "latest_report.json").is_file())
            pack = json.loads((out / "candidate_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(pack["schema"], "assetwright-mini-ai-pack-v1")
            self.assertEqual(pack["approved_count"], 1)
            self.assertEqual(len(pack["examples"]), 1)
            self.assertEqual((out / "approved_pack.json").exists(),
                             report["status"] == "promoted")

    def test_unapproved_record_rejected(self):
        example = json.loads(SEED.read_text(encoding="utf-8"))[2]
        with tempfile.TemporaryDirectory() as d:
            inbox = Path(d) / "inbox"
            inbox.mkdir()
            (inbox / "unapproved.jsonl").write_text(json.dumps(example) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                train_once(inbox, Path(d) / "out")


if __name__ == "__main__":
    unittest.main()

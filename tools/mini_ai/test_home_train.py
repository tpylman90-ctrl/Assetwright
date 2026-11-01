"""Offline quality-gate tests; no Blender, GPU or network required."""
import json
from pathlib import Path
import tempfile
import unittest

from home_train import validate, predict, train_once, SEED


class HomeTrainingTests(unittest.TestCase):
    def test_all_bundled_seed_examples_match_android_geometry_bounds(self):
        seeds = json.loads(SEED.read_text(encoding="utf-8"))
        self.assertEqual(len(seeds), 88)
        for index, seed in enumerate(seeds):
            with self.subTest(index=index, prompt=seed["prompt"]):
                self.assertEqual(validate(seed)["prompt"], seed["prompt"].strip())

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

    def test_synced_approved_feedback_is_read_and_gated(self):
        example = json.loads(SEED.read_text(encoding="utf-8"))[4]
        record = dict(example, schema="assetwright-approved-example-v1",
                      approved_by_user=True, origin="android-corrected-vehicle")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sync = root / "sync"
            sync.mkdir()
            (sync / "approved-phone.jsonl").write_text(
                json.dumps(record) + "\n", encoding="utf-8")
            report = train_once(root / "empty_inbox", root / "trained", sync)
            self.assertEqual(report["approved_user_examples"], 1)
            self.assertIn(report["status"], ("promoted", "rejected_regression"))
            if report["status"] == "promoted":
                pack = json.loads((sync / "approved_pack.json").read_text(encoding="utf-8"))
                self.assertEqual(pack["approved_count"], 1)
                self.assertEqual(pack["model_type"], "approved-example-memory")
            else:
                self.assertFalse((sync / "approved_pack.json").exists())

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

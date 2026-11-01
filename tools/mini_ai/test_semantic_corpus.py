"""Verify construction supervision is original, balanced and held out by prompt."""
import json
from collections import Counter
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"app/src/main/assets/mini_ai/construction_labels.json"
CATEGORIES={(n,m) for n in (2,4,6) for m in ("tucked","exposed")}

class ConstructionCorpusTests(unittest.TestCase):
    def test_labeled_corpus_has_complete_role_coverage(self):
        data=json.loads(SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"],"assetwright-semantic-construction-corpus-v1")
        self.assertEqual(data["version"],1)
        train=data["train"]; hold=data["heldout"]
        self.assertEqual(len(train),72)
        self.assertEqual(len(hold),24)
        train_counts=Counter((x["lift_cells"],x["mount"]) for x in train)
        hold_counts=Counter((x["lift_cells"],x["mount"]) for x in hold)
        self.assertEqual(set(train_counts),CATEGORIES)
        self.assertEqual(set(hold_counts),CATEGORIES)
        self.assertTrue(all(count>=10 for count in train_counts.values()))
        self.assertTrue(all(count>=3 for count in hold_counts.values()))
        allrows=train+hold
        prompts=[x["prompt"].strip().casefold() for x in allrows]
        self.assertEqual(len(set(prompts)),len(prompts))
        for row in allrows:
            self.assertRegex(row["origin"],r"^original-editor-labeled-")
            self.assertRegex(row["prompt"].lower(),r"(hover|hoover)")
            self.assertLessEqual(len(row["prompt"]),240)
            self.assertEqual((row["lift_cells"],row["mount"]) in CATEGORIES,True)
        source=json.dumps(data).lower()
        self.assertNotIn(".glb",source)
        self.assertNotIn("http://",source)
        self.assertNotIn("https://",source)

    def test_controlled_source_labels_are_not_cc0_semantic_guesses(self):
        data=json.loads(SOURCE.read_text(encoding="utf-8"))
        self.assertIn("original authored synthetic",data["provenance"])
        self.assertIn("no third-party",data["provenance"])

if __name__=="__main__":
    unittest.main()

"""Prevent research workflow regressions: metadata CLI and mesh CLI differ."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/forge-asset-study.yml"


class WorkflowWiringTests(unittest.TestCase):
    def test_previews_are_only_passed_to_blender_asset_study(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(text.count("--previews-dir "), 1)
        metadata = text.split("- name: Catalog all licensed model descriptions",1)[1].split("- name: Index 3D descriptions",1)[0]
        study = text.split("- name: Study selected CC0 models",1)[1].split("- name: Merge historical",1)[0]
        self.assertIn("descriptive_catalog.py", metadata)
        self.assertNotIn("--previews-dir", metadata)
        self.assertIn("forge_asset_cycle.py", study)
        self.assertIn("--previews-dir local-data/mini-ai/forge-study/review_previews", study)

    def test_review_remains_separate_from_training_and_android(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("component_review_gate.py", text)
        self.assertIn("caption_mesh_train.py", text)
        self.assertIn("review_previews/**/*.png", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("app/src/main/assets", text)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the v13 fail-closed lineage gate (no GPU or Android required)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13_lineage_preflight import EXPECTED_V10, EXPECTED_V9, REQUIRED, verify


class LineageGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.archive = root / "archive"
        self.archive.mkdir()
        self.parent = root / "v10.safetensors"
        self.identity = root / "v9.safetensors"
        self.parent.write_bytes(b"parent")
        self.identity.write_bytes(b"identity")
        for name in REQUIRED:
            (self.archive / name).write_text("{}")
        (self.archive / "research_disposition.json").write_text(json.dumps({
            "status": "research_only_rejected_parent_protected",
            "android_neural_deployed": False,
            "frozen_parent_weight_sha256": EXPECTED_V10,
            "frozen_identity_weight_sha256": EXPECTED_V9,
            "selected_on_development_3D_only": "vertex_loss_stage1",
            "blind_new_original_Kotlin_GLBS": 1152,
        }))
        (self.archive / "development_selection.json").write_text(json.dumps({
            "source_split": "development", "selected": "vertex_loss_stage1"
        }))

    def valid(self):
        def digest(path):
            return EXPECTED_V10 if path == self.parent else EXPECTED_V9
        with patch("v13_lineage_preflight.sha256", side_effect=digest):
            return verify(self.archive, self.parent, self.identity)

    def test_valid_lineage_remains_research_only(self):
        result = self.valid()
        self.assertEqual(result["status"], "lineage_verified_only_not_trained")
        self.assertFalse(result["v13_training_started"])

    def test_missing_evidence_fails_closed(self):
        (self.archive / "independent_1152_Kotlin_GLBS.json").unlink()
        with self.assertRaisesRegex(ValueError, "Missing v12 evidence"):
            self.valid()

    def test_blind_selection_fails_closed(self):
        (self.archive / "development_selection.json").write_text(json.dumps({
            "source_split": "validation", "selected": "vertex_loss_stage1"
        }))
        with self.assertRaisesRegex(ValueError, "Development selection"):
            self.valid()

    def test_real_digest_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify(self.archive, self.parent, self.identity)


if __name__ == "__main__":
    unittest.main()

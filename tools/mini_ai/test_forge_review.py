"""Forge review bridge tests; no Android SDK, Blender or external services."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from forge_review import inspect_bundle, make_proposal


def tiny_glb():
    body = {
        "asset": {"version": "2.0"},
        "meshes": [{"name": "test", "primitives": [
            {"attributes": {"POSITION": 0}, "indices": 1}
        ]}],
        "accessors": [{"count": 9}, {"count": 12}],
    }
    raw = json.dumps(body).encode("utf-8")
    raw += b" " * (-len(raw) % 4)
    return struct.pack("<IIIII", 0x46546C67, 2,
                       20 + len(raw), len(raw), 0x4E4F534A) + raw


def review_fields():
    return {
        "length": 4.8, "width": 2.05, "roofHeight": 1.52,
        "canopyLength": 1.8, "noseTaper": 0.55, "rearHaunch": 1.07
    }


def write_review(path, tamper=False):
    glb = tiny_glb()
    payload = {
        "schema": "assetwright-forge-review-v1",
        "generator": "assetwright-mini-ai",
        "prompt": "Wide hover SUV",
        "profile": "Mobile",
        "triangle_count": 4,
        "parameters": review_fields(),
        "model_sha256": "bad-hash" if tamper else hashlib.sha256(glb).hexdigest(),
        "requested_changes": "Rear needs more width",
        "share_approval": "user_exported_for_assistant_review",
    }
    with ZipFile(path, "w", ZIP_DEFLATED) as z:
        z.writestr("review.json", json.dumps(payload))
        z.writestr("model.glb", glb)


class ForgeReviewTests(unittest.TestCase):
    def test_valid_review_and_specific_proposal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.zip"
            write_review(path)
            meta, glb = inspect_bundle(path)
            self.assertEqual(meta["validated_mesh"]["triangles"], 4)
            self.assertEqual(meta["validated_mesh"]["sha256"], hashlib.sha256(glb).hexdigest())
            proposal = make_proposal(meta, {"width": 2.65}, "Increase the fitted rear body width")
            self.assertEqual(proposal["schema"], "assetwright-forge-proposal-v1")
            self.assertEqual(proposal["source_sha256"], meta["model_sha256"])
            self.assertEqual(proposal["target"]["width"], 2.65)
            self.assertEqual(proposal["target"]["length"], 4.8)

    def test_tampered_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.zip"
            write_review(path, tamper=True)
            with self.assertRaises(ValueError):
                inspect_bundle(path)

    def test_out_of_bounds_and_no_op_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.zip"
            write_review(path)
            meta, _ = inspect_bundle(path)
            with self.assertRaises(ValueError):
                make_proposal(meta, {"width": 100.0}, "Width too broad")
            with self.assertRaises(ValueError):
                make_proposal(meta, {"width": 2.05}, "No changes")
            with self.assertRaises(ValueError):
                make_proposal(meta, {"unknown": 2.0}, "Unknown dimension")


if __name__ == "__main__":
    unittest.main()

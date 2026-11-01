"""Test license gating and metadata cataloging without downloading model files."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

from library_queue import scan_once


def tiny_glb() -> bytes:
    doc = {
        "asset": {"version": "2.0"},
        "meshes": [{"name": "test", "primitives": [{
            "attributes": {"POSITION": 0}, "mode": 4
        }]}],
        "accessors": [{"count": 9}],
    }
    payload = json.dumps(doc).encode("utf-8")
    payload += b" " * (-len(payload) % 4)
    return struct.pack("<IIIII", 0x46546C67, 2, 20 + len(payload),
                       len(payload), 0x4E4F534A) + payload


class LibraryQueueTests(unittest.TestCase):
    def test_only_verified_cc0_sidecars_are_catalogued(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            inp = root / "models"
            inp.mkdir()
            path = inp / "demo.glb"
            path.write_bytes(tiny_glb())
            out = root / "candidates.jsonl"
            result = scan_once(inp, out)
            self.assertEqual(result["eligible_candidates"], 0)
            self.assertEqual(len(result["blocked"]), 1)
            sidecar = path.with_suffix(".glb.license.json")
            sidecar.write_text(json.dumps({
                "source_url": "https://example.com/cc0-mesh",
                "license": "CC0-1.0", "reviewed_by_user": True,
                "confirmed_training_allowed": True,
                "asset_family": "vehicle",
                "description": "Original labeled test mesh"
            }))
            result = scan_once(inp, out)
            self.assertEqual(result["eligible_candidates"], 1)
            lines = out.read_text().splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["status"], "candidate_not_trained")
            self.assertEqual(record["triangle_count"], 3)
            sidecar.write_text(json.dumps({"license": "unknown"}))
            result = scan_once(inp, out)
            self.assertEqual(result["eligible_candidates"], 0)
            self.assertEqual(out.read_text(), "")


if __name__ == "__main__":
    unittest.main()

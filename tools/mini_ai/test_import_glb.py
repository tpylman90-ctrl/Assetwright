"""Offline tests for the Mini AI GLB training-candidate scanner."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

from import_glb import inspect_glb


class GlbImportTests(unittest.TestCase):
    def test_valid_glb_metadata(self):
        payload = {
            "asset": {"version": "2.0"},
            "meshes": [{
                "name": "CC0 demo",
                "primitives": [{"attributes": {"POSITION": 1}, "indices": 0}]
            }],
            "accessors": [{"count": 12}, {"count": 8}],
            "materials": [{"name": "paint"}],
            "nodes": [{"mesh": 0}]
        }
        blob = json.dumps(payload).encode("utf-8")
        blob += b" " * ((-len(blob)) % 4)
        data = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(blob))
        data += struct.pack("<II", len(blob), 0x4E4F534A) + blob
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.glb"
            path.write_bytes(data)
            stats = inspect_glb(path)
        self.assertEqual(stats["triangle_count"], 4)
        self.assertEqual(stats["mesh_count"], 1)
        self.assertEqual(stats["material_count"], 1)
        self.assertEqual(stats["unmeasured_primitive_count"], 0)

    def test_reject_bad_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.glb"
            path.write_bytes(b"not a glb")
            with self.assertRaises(ValueError):
                inspect_glb(path)


if __name__ == "__main__":
    unittest.main()

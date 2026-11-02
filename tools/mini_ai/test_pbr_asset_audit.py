"""Fast regression checks for GLB technical-fidelity auditor."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pbr_asset_audit import GlbFormatError, inspect


def fixture(path, *, extensions=None, uv=True):
    # Small but structurally sufficient GLB. No proprietary assets included.
    attr = {"POSITION": 0, "NORMAL": 1}
    if uv:
        attr["TEXCOORD_0"] = 2
    material = {
        "name": "Test PBR",
        "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0},
            "metallicRoughnessTexture": {"index": 1}
        },
        "normalTexture": {"index": 2}
    }
    doc = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": 32}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 8},
            {"buffer": 0, "byteOffset": 8, "byteLength": 8},
            {"buffer": 0, "byteOffset": 16, "byteLength": 8}
        ],
        "accessors": [
            {"componentType": 5126, "count": 3, "type": "VEC3",
             "min": [-1, 0, -2], "max": [1, 2, 2]},
            {"componentType": 5126, "count": 3, "type": "VEC3"},
            {"componentType": 5126, "count": 3, "type": "VEC2"}
        ],
        "meshes": [{"name": "original-test-vehicle",
                    "primitives": [{"attributes": attr, "material": 0}]}],
        "materials": [material],
        "textures": [{"source": 0}, {"source": 1}, {"source": 2}],
        "images": [{"bufferView": i, "mimeType": "image/png"}
                   for i in range(3)]
    }
    if extensions:
        doc["extensionsRequired"] = extensions
    encoded = json.dumps(doc, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    binary = b"\x00" * 32
    body = (struct.pack("<I4s", len(encoded), b"JSON") + encoded
            + struct.pack("<I4s", len(binary), b"BIN\x00") + binary)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12+len(body))+body)


class AuditTest(unittest.TestCase):
    def test_full_material_report_with_no_aesthetic_score(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/"example.glb"
            fixture(p)
            r = inspect(p)
            self.assertEqual(r["triangles"], 1)
            self.assertEqual(r["bounds_xyz_m"], [2, 2, 4])
            self.assertTrue(r["geometry_has_uvs"])
            self.assertTrue(r["has_pbr_textures"])
            self.assertEqual(len(r["textures"]), 3)
            self.assertFalse(r["visual_quality_verified"])

    def test_no_uv_reports_unready_for_baking(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/"example.glb"
            fixture(p, uv=False)
            self.assertFalse(inspect(p)["geometry_has_uvs"])

    def test_no_implicit_compressed_mesh_support(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/"example.glb"
            fixture(p, extensions=["EXT_meshopt_compression"])
            with self.assertRaises(GlbFormatError):
                inspect(p)

    def test_reject_truncated_data(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/"bad.glb"
            p.write_bytes(b"glTF")
            with self.assertRaises(GlbFormatError):
                inspect(p)


if __name__ == "__main__":
    unittest.main()

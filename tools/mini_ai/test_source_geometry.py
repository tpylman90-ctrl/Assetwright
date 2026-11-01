"""No-network security and geometry descriptor tests for Blender source intake."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

from source_geometry import file_choices, valid_url, unpack_source, inspect_with_blender


class SourceGeometryTests(unittest.TestCase):
    def test_accept_only_official_small_mesh_source_files(self):
        tree = {
            "1k": {
                "blend": {"url": "https://dl.polyhaven.org/file/Models/1k/model.blend", "size": 1500},
                "fbx": {"url": "https://dl.polyhaven.org/file/Models/2k/model.fbx", "size": 3200},
                "obj": {"url": "https://dl.polyhaven.org/file/Models/1k/model.obj", "size": 15000},
                "texture": {"url": "https://dl.polyhaven.org/file/Models/1k/diffuse.png", "size": 10}
            },
            "evil": {"url": "https://example.org/asset.glb", "size": 100},
            "huge": {"url": "https://dl.polyhaven.org/huge.zip", "size": 80 * 1024 * 1024}
        }
        sources = file_choices(tree)
        self.assertEqual({x["format"] for x in sources}, {"blend", "fbx", "obj"})
        self.assertEqual(sources[0]["format"], "blend")
        for url in ("http://dl.polyhaven.org/file/model.blend",
                    "https://evilpolyhaven.org/model.fbx",
                    "https://dl.polyhaven.org.evil.org/model.glb",
                    "https://user:pw@dl.polyhaven.org/model.glb"):
            self.assertFalse(valid_url(url))
        self.assertTrue(valid_url("https://dl.polyhaven.org/models/foo.blend"))

    def test_zip_cannot_escape_destination_and_only_mesh_extracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            archive = folder / "model.zip"
            with zipfile.ZipFile(archive, "w") as dst:
                dst.writestr("../evil.fbx", "malicious")
                dst.writestr("scenes/model.obj", "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3")
                dst.writestr("scripts/exploit.py", "raise RuntimeError('never execute')")
            extracted = unpack_source(archive, folder)
            self.assertEqual(extracted.name, "source.obj")
            self.assertFalse((folder.parent / "evil.fbx").exists())
            self.assertFalse((folder / "scripts/exploit.py").exists())

    def test_geometry_extractor_keeps_only_validated_feature_vector(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = {"format": "blend", "url": "https://dl.polyhaven.org/foo.blend",
                         "size": 4, "md5": None}
            def fake_download(_candidate, destination):
                destination.write_bytes(b"test")
                return {"source_sha256": "a" * 64, "source_bytes": 4}
            def fake_blender(argv, **kwargs):
                output = Path(argv[-1])
                output.write_text(json.dumps({
                    "schema": "assetwright-geometry-descriptor-v1",
                    "features": [.1, .2, .3, .4, .5, .6, .7, .8],
                    "mesh_parts": 2, "triangles": 100,
                }))
                return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            with patch("source_geometry.download", side_effect=fake_download), \
                 patch("source_geometry.subprocess.run", side_effect=fake_blender):
                result = inspect_with_blender(candidate)
            self.assertEqual(len(result["features"]), 8)
            self.assertEqual(result["source_format"], "blend")
            self.assertEqual(result["source_sha256"], "a" * 64)

    def test_reject_bad_extraction_vector(self):
        candidate = {"format": "glb", "url": "https://dl.polyhaven.org/model.glb",
                     "size": None, "md5": None}
        def fake_download(_, destination):
            destination.write_bytes(b"test")
            return {"source_sha256": "b" * 64, "source_bytes": 4}
        def fake_blender(argv, **kwargs):
            Path(argv[-1]).write_text(json.dumps({
                "schema": "assetwright-geometry-descriptor-v1",
                "features": [-1] * 8
            }))
            return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch("source_geometry.download", side_effect=fake_download), \
             patch("source_geometry.subprocess.run", side_effect=fake_blender):
            with self.assertRaises(ValueError):
                inspect_with_blender(candidate)


if __name__ == "__main__":
    unittest.main()

"""Real GLB buffer parsing regression tests, not metadata-only assertions."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from generated_glb_critic import inspect, evaluate
from generator_quality_loop import run


def synthetic_glb(path:Path, *, corrupt_index=False):
    # Valid glTF2 asset with a true triangle's position and index buffer.
    vertices=struct.pack("<9f", 0,0,0, 1,0,0, 0,1,0)
    indices=struct.pack("<3I", 0,1,12 if corrupt_index else 2)
    binary=vertices+indices
    doc={"asset":{"version":"2.0"},"buffers":[{"byteLength":len(binary)}],
         "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":len(vertices)},
                        {"buffer":0,"byteOffset":len(vertices),"byteLength":len(indices)}],
         "accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3"},
                      {"bufferView":1,"componentType":5125,"count":3,"type":"SCALAR"}],
         "meshes":[{"name":"Sculpted continuous body",
                    "primitives":[{"attributes":{"POSITION":0},"indices":1,"mode":4}]}],
         "nodes":[{"mesh":0}],"scenes":[{"nodes":[0]}],"scene":0}
    encoded=json.dumps(doc,separators=(",",":")).encode()
    encoded+=b" " * ((-len(encoded))%4)
    length=12+8+len(encoded)+8+len(binary)
    path.write_bytes(
       struct.pack("<III",0x46546c67,2,length)+
       struct.pack("<II",len(encoded),0x4e4f534a)+encoded+
       struct.pack("<II",len(binary),0x004e4942)+binary
    )


def target(sha:str):
    return {"schema":"assetwright-generated-vehicle-target-v1",
            "original_procedural_asset":True,
            "expected_engine":"android-native-MiniGeometry",
            "source_glb_sha256":sha,"case":"fixture",
            "variant":"baseline","drive_count":2,"lift_cells":4,
            "mount":"exposed","roof_height":1.4}


class RealGlbCriticTests(unittest.TestCase):
    def test_reads_actual_position_and_triangle_data(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"valid.glb"
            synthetic_glb(file)
            audit=inspect(file)
            self.assertEqual(audit["triangles"],1)
            self.assertEqual(audit["invalid_triangles"],0)
            self.assertEqual(audit["mesh_parts"],1)
            self.assertEqual(audit["parts"][0]["max"],[1.,1.,0.])
            self.assertEqual(audit["parts"][0]["boundary_edges"],3)
            rating=evaluate(audit,target(audit["model_sha256"]))
            self.assertFalse(rating["passed"])
            self.assertEqual(rating["score"],0)
            self.assertFalse(rating["checks"]["part_count_matches"])
            self.assertEqual(rating["training_label_status"],"benchmark_score_not_verified_supervision")

    def test_bad_indices_and_corrupted_glb_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"bad.glb"
            synthetic_glb(path,corrupt_index=True)
            with self.assertRaisesRegex(ValueError,"Invalid vertex index"):
                inspect(path)
            path.write_bytes(path.read_bytes()[:35])
            with self.assertRaises(ValueError):
                inspect(path)

    def test_benchmark_rejects_mismatched_source_hash_and_never_self_trains(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            file=root/"fixture__baseline.glb"
            synthetic_glb(file)
            data=target("f"*64)
            (root/"fixture__baseline.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"checksum"):
                run(root,root/"report.json")
            data["source_glb_sha256"]=hashlib.sha256(file.read_bytes()).hexdigest()
            (root/"fixture__baseline.json").write_text(json.dumps(data))
            report=run(root,root/"report.json")
            self.assertEqual(report["decision"] if "decision" in report else
                             report["results"][0]["decision"],"baseline_failed_manual_review")
            self.assertEqual(report["promoted_to_training"],0)
            self.assertFalse(report["android_model_updated"])

if __name__=="__main__":
    unittest.main()

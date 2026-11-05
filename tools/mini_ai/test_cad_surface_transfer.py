"""Offline source-geometry gates. Synthetic STL shapes NEVER count as research evidence."""
from __future__ import annotations

import hashlib
import json
import math
import struct
import unittest
import numpy as np

from cad_surface_teacher import (
    descriptors,decode_stl,safe_stl_bytes,TARGETS,GEOMETRY_SCHEMA
)
from cad_surface_student import (
    verify,model_fit,predict,features,split_internal,score,MODEL
)

def cube_triangles():
    # Six square faces with two triangles each; physical side length 2.
    corners=np.array([
        [-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
        [-1,-1, 1],[1,-1, 1],[1,1, 1],[-1,1,1]
    ],dtype=np.float32)
    quads=[
        (0,3,2,1),(4,5,6,7),
        (0,1,5,4),(3,7,6,2),
        (0,4,7,3),(1,2,6,5)
    ]
    triangles=[]
    for a,b,c,d in quads:
        triangles.extend((corners[[a,b,c]],corners[[a,c,d]]))
    return np.asarray(triangles)

def binary_stl(faces):
    header=bytearray(b"AssetWright synthetic test; never training evidence".ljust(80,b" "))
    header+=struct.pack("<I",len(faces))
    for face in faces:
        header+=struct.pack("<12fH",*(0.,0.,0.),
                          *face[0],*face[1],*face[2],0)
    return bytes(header)

def corpus(n,split):
    rows=[]
    for i in range(n):
        operations=[
            ["rect","extrude","circle","cutBlind","fillet"],
            ["circle","revolve","shell","chamfer"],
            ["ellipse","sweep","rotate","cut"],
            ["polygon","extrude","polarArray","mirror"]
        ][i%4]
        literal=[0.]*18
        literal[i%6]=.11+(i%7)*.09
        literal[10]=.4+(i%5)*.08
        literal[17]=.2+(i%3)*.12
        target=[
            min(1.,.3+literal[10]*.5+(i%4)*.07),
            min(1.,.2+literal[17]*.55+(i%4)*.04),
            .65+(i%4)*.11+literal[i%6]*.2,
            min(1.,.11+literal[10]*.22),
            min(1.,.19+literal[17]*.23)
        ]
        rows.append({
            "source_id":f"{split}_fixture_{i:05d}",
            "code_sha256":hashlib.sha256(f"{split}:{i}:script".encode()).hexdigest(),
            "stl_sha256":hashlib.sha256(f"{split}:{i}:mesh".encode()).hexdigest(),
            "split":split,"operations":operations,
            "safe_numeric_cad_features":literal,
            "surface_target":target,
            "surface_audit":{"triangles":12}
        })
    return {
        "schema":GEOMETRY_SCHEMA,"license":"Apache-2.0",
        "dataset":"ADSKAILab/Zero-To-CAD-100k",
        "official_split":split,"dataset_revision":"b"*40,
        "source_offset":2400 if split=="train" else 1800,
        "downloaded_scripts_executed":False,
        "downloaded_meshes_exported_as_native":False,
        "mesh_bytes_retained":False,"records":rows
    }

class CadSurfaceTransferTests(unittest.TestCase):
    def test_actual_mesh_teacher_has_scale_invariant_geometric_targets(self):
        original=cube_triangles()
        raw=binary_stl(original)
        self.assertEqual(len(raw),84+50*12)
        decoded=decode_stl(safe_stl_bytes(raw))
        self.assertTrue(np.allclose(decoded,original))
        x,meta=descriptors(decoded)
        self.assertEqual(len(x),len(TARGETS))
        self.assertAlmostEqual(x[0],1.,places=6)
        self.assertAlmostEqual(x[1],1.,places=6)
        self.assertAlmostEqual(x[2],1.,places=6)
        self.assertGreater(x[3],.3)
        self.assertEqual(meta["triangles"],12)
        rescaled,_=descriptors(decoded*3.5)
        self.assertTrue(np.allclose(x,rescaled,atol=1e-7))

    def test_corrupt_and_excessive_binary_mesh_is_rejected(self):
        raw=binary_stl(cube_triangles())
        with self.assertRaises(ValueError):
            decode_stl(raw[:-1])
        with self.assertRaises(ValueError):
            decode_stl(raw+b"tampering")
        with self.assertRaises(ValueError):
            decode_stl(raw[:80]+struct.pack("<I",999999)+raw[84:])
        with self.assertRaises(ValueError):
            safe_stl_bytes(b"solid imaginary bad STL")

    def test_own_model_never_sees_teacher_target_at_inference(self):
        train_doc=corpus(300,"train")
        # Negative numeric literal groups legitimately have signed fraction -1;
        # their bounds are [-1,1], unlike the other [0,1] features.
        train_doc["records"][0]["safe_numeric_cad_features"][3]=-1.0
        train,valid=verify(train_doc,corpus(80,"validation"))
        fitted,internal=split_internal(train)
        student=model_fit(fitted,10.,True)
        student_ops=model_fit(fitted,10.,False)
        inferred=predict(student,valid)
        self.assertEqual(inferred.shape,(80,5))
        self.assertEqual(predict(student_ops,valid).shape,(80,5))
        scorecard=score(inferred,valid)
        self.assertGreater(scorecard["sources"],64)
        cloned=dict(valid[0])
        before=features(cloned,True)
        cloned["surface_target"]=[0.]*5
        cloned["stl_sha256"]="f"*64
        self.assertTrue(np.array_equal(before,features(cloned,True)))

    def test_cad_source_hash_leak_and_source_revision_are_rejected(self):
        train=corpus(300,"train")
        valid=corpus(80,"validation")
        valid["records"][0]["stl_sha256"]=train["records"][0]["stl_sha256"]
        with self.assertRaisesRegex(ValueError,"collision"):
            verify(train,valid)
        valid=corpus(80,"validation")
        valid["dataset_revision"]="c"*40
        with self.assertRaisesRegex(ValueError,"revision"):
            verify(train,valid)
        valid=corpus(80,"validation")
        valid["source_offset"]=0
        with self.assertRaises(ValueError):
            verify(train,valid)

    def test_user_scripts_are_never_run_as_part_of_stl_read(self):
        sentinel="/tmp/assetwright-stl-teacher-must-not-run"
        from pathlib import Path
        self.assertFalse(Path(sentinel).exists())
        raw=binary_stl(cube_triangles())
        self.assertEqual(len(decode_stl(raw)),12)
        self.assertFalse(Path(sentinel).exists())

if __name__=="__main__":
    unittest.main()

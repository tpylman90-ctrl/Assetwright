"""Offline deterministic proof of original visual delta school integrity."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import importlib.util

from dino_delta_school import (
    BASELINES,EXPECTED,FAMILIES,LEVELS,VIEWS,MANIFEST,
    checked_manifest,expected_changes,framing_bounds)
from dino_delta_student import INPUT_DIM,image_features


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def fixture(directory):
    from PIL import Image
    expected=expected_changes()
    records=[]
    seen_images={}
    for stem,(split,family,op,level,base) in sorted(expected.items()):
        name_map={}
        for role,case in (("before",base),("after",stem)):
            names={};hashes={}
            for view in VIEWS:
                name=case+"__"+view+".png"
                path=directory/name
                if name not in seen_images:
                    Image.new("RGB",(24,24),(176,187,199)).save(path)
                    seen_images[name]=hashlib.sha256(path.read_bytes()).hexdigest()
                names[view]=name
                hashes[view]=seen_images[name]
            name_map[role]=(names,hashes)
        records.append({
            "case":stem,"split":split,"family":family,"operation":op,
            "strength":level,"baseline_case":base,
            "baseline_glb_sha256":sha(base),
            "modified_glb_sha256":sha(stem),
            "measured_morphology_delta":[.1,.2,.3,.4,.5,.6],
            "before_view_files":name_map["before"][0],
            "before_view_sha256":name_map["before"][1],
            "after_view_files":name_map["after"][0],
            "after_view_sha256":name_map["after"][1],
        })
    return {
        "schema":MANIFEST,"generator":"AssetWright-Kotlin-AdvancedFormLab",
        "study_id":"delta_v1",
        "views":list(VIEWS),"source_count":EXPECTED+BASELINES,
        "paired_examples":EXPECTED,"renderer":"fixed-family-orthographic-clay",
        "external_geometry_used":False,"records":records
    }


@unittest.skipUnless(importlib.util.find_spec("PIL") is not None,
                     "Pillow needed only for optional visual research")
class OriginalDeltaSchoolTests(unittest.TestCase):
    def test_frozen_source_family_and_strength_holdouts(self):
        self.assertEqual(len(expected_changes()),468)
        self.assertEqual(sum(k.startswith("train__") for k in expected_changes()),360)
        self.assertEqual(sum(k.startswith("development__") for k in expected_changes()),54)
        self.assertEqual(sum(k.startswith("validation__") for k in expected_changes()),54)
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))

    def test_real_before_after_pixel_changes_and_ablation(self):
        from PIL import Image,ImageDraw
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            row={"before_view_files":{},"after_view_files":{}}
            for view in VIEWS:
                before=Image.new("RGB",(224,224),(20,26,37))
                after=before.copy()
                dr=ImageDraw.Draw(before)
                dr.ellipse((48,50,145,150),fill=(170,185,195))
                dr=ImageDraw.Draw(after)
                dr.ellipse((40,50,177,150),fill=(170,185,195))
                for name,image in (("before",before),("after",after)):
                    path=folder/(name+"__"+view+".png")
                    image.save(path)
                    row[name+"_view_files"][view]=path.name
            features=image_features(row,folder)
            last_only=image_features(row,folder,after_only=True)
            self.assertEqual(len(features),INPUT_DIM)
            self.assertNotEqual(features,last_only)
            self.assertTrue(all(abs(x)<=1.000001 for x in features))
            self.assertEqual(features,image_features(row,folder))

    def test_shared_camera_frame_encompasses_all_eight_bounds_corners(self):
        mins=[-3.,-.7,-2.]
        maxes=[2.,1.6,3.]
        fit=framing_bounds([{"min":mins,"max":maxes}])
        self.assertEqual(len(fit),1)
        self.assertEqual(len(fit[0][1]),8)
        self.assertEqual(tuple(mins),min(fit[0][1]))

    def test_strict_multi_view_mesh_hash_and_baseline_alignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            doc=fixture(folder)
            self.assertEqual(len(checked_manifest(doc,folder)),EXPECTED)
            doc["records"][2]["baseline_glb_sha256"]="0"*64
            with self.assertRaisesRegex(ValueError,"Different original baselines"):
                checked_manifest(doc,folder)
            doc=fixture(folder)
            doc["records"][0]["operation"]="TANGENT_SWEEP" if (
                doc["records"][0]["operation"]!="TANGENT_SWEEP") else "SECTION_LOFT"
            with self.assertRaisesRegex(ValueError,"identity mismatch"):
                checked_manifest(doc,folder)
            doc=fixture(folder)
            p=folder/doc["records"][0]["after_view_files"][VIEWS[0]]
            p.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError,"Tampered"):
                checked_manifest(doc,folder)


if __name__=="__main__":
    unittest.main()

"""Offline tests: source isolation, label-free image features, split inventory."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from dino_native_visual_school import (
    VIEWS,FAMILIES,LEVELS,MANIFEST_SCHEMA,MODEL,checked_manifest,expected_stems)
from dino_native_visual_student import FEATURE_DIM,image_features


class NativeDinoSchoolTests(unittest.TestCase):
    def test_source_families_and_levels_are_truly_disjoint(self):
        expected=expected_stems()
        self.assertEqual(len(expected),252)
        self.assertEqual(sum(x[0]=="train" for x in expected.values()),180)
        self.assertEqual(sum(x[0]=="development" for x in expected.values()),36)
        self.assertEqual(sum(x[0]=="validation" for x in expected.values()),36)
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))

    def test_pixel_student_has_no_filename_label_inputs(self):
        try:
            from PIL import Image,ImageDraw
        except ImportError:
            self.skipTest("Pillow native-DINO study requires optional research dependencies")
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)
            files=[]
            for view in VIEWS:
                p=source/(view+".png")
                im=Image.new("RGB",(224,224),(20,26,37))
                dr=ImageDraw.Draw(im)
                dr.ellipse((40,40,184,184),fill=(175,187,199))
                im.save(p)
                files.append(p)
            x=image_features(files)
            self.assertEqual(len(x),FEATURE_DIM)
            self.assertEqual(x,image_features(files))
            self.assertTrue(all(0<=v<=1 for v in x))
            im=Image.new("RGB",(224,224),(20,26,37))
            im.save(files[0])
            self.assertNotEqual(x,image_features(files))

    def test_manifest_rejects_image_swap_and_duplicate_source(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow native-DINO study requires optional research dependencies")
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            observations=[]
            for stem,(split,family,op,strength) in expected_stems().items():
                digest=hashlib.sha256(stem.encode()).hexdigest()
                files={};hashes={}
                for view in VIEWS:
                    name=stem+"__"+view+".png"
                    p=directory/name
                    Image.new("RGB",(32,32),(25,51,83)).save(p)
                    files[view]=name
                    hashes[view]=hashlib.sha256(p.read_bytes()).hexdigest()
                observations.append({
                    "case":stem,"split":split,"family":family,"operation":op,
                    "strength":strength,"source_glb_sha256":digest,
                    "view_files":files,"view_sha256":hashes})
            manifest={"schema":MANIFEST_SCHEMA,
                      "native_generator":"AssetWright-AdvancedFormLab",
                      "source_count":252,"views":list(VIEWS),
                      "records":observations}
            self.assertEqual(len(checked_manifest(manifest,directory)),252)
            observations[1]["source_glb_sha256"]=observations[0]["source_glb_sha256"]
            with self.assertRaisesRegex(ValueError,"Repeated"):
                checked_manifest(manifest,directory)
            observations[1]["source_glb_sha256"]=hashlib.sha256(observations[1]["case"].encode()).hexdigest()
            p=directory/observations[0]["view_files"][VIEWS[0]]
            p.write_bytes(b"image tampering")
            with self.assertRaisesRegex(ValueError,"Tampered"):
                checked_manifest(manifest,directory)


if __name__=="__main__":
    unittest.main()

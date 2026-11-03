"""Safety and split-integrity tests: teacher never supplies output mesh."""
import hashlib
import tempfile
from pathlib import Path
import unittest
from visual_transfer_student import (
    EMBEDDINGS,MANIFEST,MIN_SOURCES,MODEL,PARAMS,fit,
    normalize_parameters,parse_rows,predict,project_teacher,
)
from render_visual_transfer import original_recipe

def fixture(count=48):
    records=[]; embeddings=[]
    for i in range(count):
        case=f"independent_{i:03d}"
        sha=hashlib.sha256(f"native-own-glb-{i}".encode()).hexdigest()
        views={v:hashlib.sha256(f"{case}-{v}".encode()).hexdigest()
               for v in ("front","side","top","three_quarter")}
        group=i%3
        prompt=(f"Original hover {'suv' if group==0 else 'racer' if group==1 else 'coupe'} "
                f"with {'compact' if i%2 else 'long'} aerodynamic body and "
                f"{'wide' if i%4 else 'slim'} panoramic canopy design")
        dimensions={"length":4.5+.14*(i%8),"width":1.8+.12*(i%7),
                    "roof_height":1.2+.08*(i%6),"canopy_length":1.5+.11*(i%8),
                    "nose_taper":.42+.026*(i%7),"rear_haunch":1.02+.019*(i%9)}
        records.append({"sample_id":case+"__baseline","source_group":case,
                        "prompt":prompt,"source_glb_sha256":sha,
                        "expected_engine":"android-native-MiniGeometry",
                        "original_procedural_asset":True,"view_sha256":views,
                        "parameters":dimensions})
        features=[float((j%7)/7+.2*group+.03*(i%9)) for j in range(384)]
        embeddings.append({"sample_id":case+"__baseline",
                           "source_glb_sha256":sha,
                           "view_sha256":views.copy(),"embedding":features})
    return ({"schema":MANIFEST,"examples":records},
            {"schema":EMBEDDINGS,"model_id":"facebook/dinov2-small","features":embeddings})

class VisualTransferStudentTests(unittest.TestCase):
    def test_exact_native_parameter_bounds(self):
        values={k:(lo+hi)/2 for k,(lo,hi) in PARAMS.items()}
        self.assertEqual(len(normalize_parameters(values)),6)
        with self.assertRaises(ValueError):
            normalize_parameters({**values,"width":99})

    def test_source_disjoint_gate_rejects_small_sample(self):
        left,right=fixture(6)
        report,student=fit(left,right)
        self.assertEqual(report["status"],"insufficient_independent_designs")
        self.assertEqual(report["required_design_groups"],MIN_SOURCES)
        self.assertIsNone(student)

    def test_rejects_unreviewed_teacher_mesh_or_mixed_provenance(self):
        left,right=fixture(5)
        left["examples"][0]["original_procedural_asset"]=False
        with self.assertRaisesRegex(ValueError,"external/generated-teacher"):
            parse_rows(left,right)
        left,right=fixture(5)
        right["features"][0]["view_sha256"]["front"]="0"*64
        with self.assertRaisesRegex(ValueError,"does not match"):
            parse_rows(left,right)

    def test_no_duplicate_meshes_across_design_splits(self):
        left,right=fixture(2)
        left["examples"][1]["source_glb_sha256"]=left["examples"][0]["source_glb_sha256"]
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            parse_rows(left,right)

    def test_teacher_features_only_auxiliary_and_not_at_inference(self):
        left,right=fixture(50)
        report,student=fit(left,right)
        self.assertIsNotNone(student)
        self.assertEqual(student["schema"],MODEL)
        self.assertFalse(student["android_deployable"])
        self.assertEqual(student["inference_input"],"text_only")
        self.assertEqual(report["holdout_examples"]+report["train_examples"],50)
        self.assertFalse(report["external_model_generates_meshes"])
        self.assertIn(report["status"],("validated_research_student",
                                        "transfer_failed_to_beat_text_baseline"))
        proposal=predict(student,"Wide aerodynamic hover racer with a swept canopy")
        self.assertTrue(proposal["research_only"])
        self.assertFalse(proposal["uses_external_mesh"])
        for k,(lo,hi) in PARAMS.items():
            self.assertTrue(lo<=proposal["parameters"][k]<=hi)

    def test_teacher_dimension_and_zero_feature_rejected(self):
        self.assertEqual(len(project_teacher([.01]*384)),24)
        with self.assertRaises(ValueError): project_teacher([.01]*10)

    def test_renderer_rejects_unmatched_or_external_mesh(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"own_test__baseline.glb"
            path.write_bytes(b"fake-hash-test-fixture")
            actual=hashlib.sha256(path.read_bytes()).hexdigest()
            vals={k:(lo+hi)/2 for k,(lo,hi) in PARAMS.items()}
            original={"schema":"assetwright-generated-vehicle-target-v1",
                      "original_procedural_asset":True,
                      "expected_engine":"android-native-MiniGeometry",
                      "case":"own_test",
                      "prompt":"Original hovercraft with carefully sculpted body",
                      "source_glb_sha256":actual,"parameters":vals}
            self.assertEqual(original_recipe(path,original)["source_glb_sha256"],actual)
            with self.assertRaisesRegex(ValueError,"hash"):
                original_recipe(path,{**original,"source_glb_sha256":"0"*64})
            with self.assertRaisesRegex(ValueError,"non-native"):
                original_recipe(path,{**original,"original_procedural_asset":False})

if __name__=="__main__":
    unittest.main()

import unittest
from zero_to_cad_visual_student import fit,prepared,input_features,MODEL
from zero_to_cad_dinov2_teacher import SCHEMA as TEACHER,MODEL as DINO
from test_zero_to_cad import manifest

def features(doc):
    return {"schema":TEACHER,"model_id":DINO,"source_dataset":doc["dataset"],
            "source_split":doc["split"],"teacher_frozen":True,
            "records":[{"source_id":r["source_id"],"code_sha256":r["code_sha256"],
                        "view_sha256":r.get("view_sha256"),
                        "frozen_visual_embedding":[.3+.01*(i%7)+.001*(j%12)
                         for j in range(384)]}
                       for i,r in enumerate(doc["records"])]}

class VisualKnowledgeTransferTests(unittest.TestCase):
    def test_input_is_operations_only(self):
        self.assertGreater(len(input_features(["rect","extrude","fillet"],12)),50)
        with self.assertRaises(ValueError):
            input_features(["imported_external_mesh"],12)
    def test_teacher_source_alignment(self):
        m=manifest(3,"train");e=features(m)
        self.assertEqual(len(prepared(m,e,"train")),3)
        e["records"][0]["code_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"alignment"):
            prepared(m,e,"train")
    def test_owned_student_is_not_external_geometry_generator(self):
        tr=manifest(30,"train");valid=manifest(12,"validation")
        report,model=fit(tr,features(tr),valid,features(valid))
        self.assertIsNotNone(model)
        self.assertEqual(model["schema"],MODEL)
        self.assertFalse(model["inference_needs_teacher"])
        self.assertFalse(model["approved_for_geometry_generation"])
        self.assertFalse(model["android_deployable"])
        self.assertIn(report["status"],("validated_research_visual_student",
                                        "visual_student_rejected_holdout"))
    def test_heldout_leakage_is_rejected(self):
        tr=manifest(30,"train");valid=manifest(12,"validation")
        valid["records"][0]["code_sha256"]=tr["records"][0]["code_sha256"]
        with self.assertRaisesRegex(ValueError,"leakage"):
            fit(tr,features(tr),valid,features(valid))
if __name__=="__main__": unittest.main()

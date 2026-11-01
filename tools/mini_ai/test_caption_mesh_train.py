import hashlib
import unittest

from caption_mesh_train import fit,valid_rows


def pair(i:int,group:int)->dict:
    sha=hashlib.sha256(f"original-test-model-{i}".encode()).hexdigest()
    return {
       "source_object_id":f"original_{i}",
       "source":"Poly Haven","license":"CC0-1.0",
       "source_mesh_sha256":sha,
       "caption":("An extended flat mechanical vehicle chassis with wheel housings and long body"
                  if group else
                  "A compact rounded industrial turbine housing with enclosed cylindrical motor"),
       "geometry_features":([.16,.38,.04,.01,.5,.7,.12,.02] if group else
                            [.65,.84,.05,.01,.6,.8,.17,.02])
    }


class CaptionMeshTrainingTests(unittest.TestCase):
    def test_minimum_real_mesh_labels_gate(self):
        doc={"schema":"assetwright-grounded-text-mesh-pairs-v1",
             "pairs":[pair(i,i%2) for i in range(12)]}
        result,model=fit(doc)
        self.assertEqual(result["status"],"insufficient_real_mesh_pairs")
        self.assertIsNone(model)

    def test_source_disjoint_actual_mesh_descriptor_training(self):
        doc={"schema":"assetwright-grounded-text-mesh-pairs-v1",
             "pairs":[pair(i,i%2) for i in range(160)]}
        report,model=fit(doc)
        self.assertEqual(report["grounded_pairs"],160)
        self.assertGreaterEqual(report["holdout_models"],6)
        self.assertEqual(report["status"],"trained_passed_validation")
        self.assertLess(report["candidate_mse"],report["baseline_mse"])
        self.assertFalse(model["android_deployable"])
        self.assertEqual(model["feature_count"],8)
        self.assertEqual(len(model["source_model_hashes"]),report["train_models"])

    def test_invalid_license_and_duplicate_mesh_hash_are_discarded(self):
        records=[pair(i,i%2) for i in range(5)]
        records[1]["source_mesh_sha256"]=records[0]["source_mesh_sha256"]
        records[2]["license"]="CC-BY-NC"
        records[3]["geometry_features"]=[-1]*8
        rows=valid_rows({"schema":"assetwright-grounded-text-mesh-pairs-v1",
                         "pairs":records})
        self.assertEqual(len(rows),2)


if __name__=="__main__":
    unittest.main()

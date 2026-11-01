import unittest
from part_role_proposals import propose
from component_graph import build_graph
from component_review_gate import pending_pairs, approve


def examples():
    graph=build_graph([
        {"min":[0,0,0],"max":[1,1,1],"triangles":200},
        {"min":[1,0,0],"max":[1.3,.6,.5],"triangles":100,
         "role_proposal":propose("Engine_Housing.003")}
    ],[0,0,0],[1.4,1.3,1.2])
    # Ambiguous names are intentionally not auto-approved.
    return {"schema":"assetwright-grounded-text-mesh-pairs-v1","pairs":[{
        "source_object_id":"original_model",
        "source_page":"https://polyhaven.com/a/original_model",
        "source_mesh_sha256":"a"*64,"caption":"Original mechanical engine",
        "component_graph":graph
    }]}


class ComponentReviewGateTests(unittest.TestCase):
    def test_role_proposals_fail_closed_on_generic_and_ambiguous_names(self):
        self.assertIsNone(propose("Cube.002"))
        self.assertIsNone(propose("Mesh_003"))
        self.assertIsNone(propose("wheel_engine_housing"))
        self.assertEqual(propose("Wheel_FL")["candidate_role"],"wheel")
        self.assertEqual(propose("Windscreen")["candidate_role"],"canopy")
        self.assertEqual(propose("a bronze axle")["status"],"requires_visual_verification")

    def test_review_queue_never_promotes_weak_labels(self):
        tasks,stats=pending_pairs(examples())
        self.assertEqual(stats["grounded_model_graphs"],1)
        self.assertEqual(stats["weak_role_candidates"],1)
        self.assertEqual(stats["approved_semantic_labels"],0)
        self.assertEqual(tasks["tasks"][0]["suggested_role"],"engine")

    def test_real_source_sha_graph_node_evidence_are_required(self):
        source=examples()
        task=pending_pairs(source)[0]["tasks"][0]
        record={
            "source_object_id":"original_model",
            "source_mesh_sha256":"a"*64,
            "graph_component_id":task["graph_component_id"],
            "approved_role":"engine",
            "reviewer":"Forge review",
            "verification_method":"reviewed_multiview_render",
            "evidence_sha256":"b"*64
        }
        manifest={"schema":"assetwright-reviewed-component-roles-v1","reviews":[record]}
        labels,report=approve(source,manifest)
        self.assertEqual(report["approved_review_assertions"],1)
        self.assertFalse(labels["android_deployable"])
        bad={**record,"source_mesh_sha256":"c"*64}
        _,report=approve(source,{"schema":manifest["schema"],"reviews":[bad]})
        self.assertEqual(report["approved_review_assertions"],0)
        self.assertEqual(len(report["rejected_reviews"]),1)
        bad={**record,"evidence_sha256":"a"*64}
        _,report=approve(source,{"schema":manifest["schema"],"reviews":[bad]})
        self.assertEqual(report["approved_review_assertions"],0)

    def test_review_must_refer_to_a_real_component(self):
        source=examples()
        record={
            "source_object_id":"original_model","source_mesh_sha256":"a"*64,
            "graph_component_id":999,"approved_role":"engine",
            "reviewer":"Forge reviewer","verification_method":"reviewed_multiview_render",
            "evidence_sha256":"b"*64
        }
        _,report=approve(source,{"schema":"assetwright-reviewed-component-roles-v1",
                                 "reviews":[record]})
        self.assertEqual(report["approved_review_assertions"],0)


if __name__=="__main__":
    unittest.main()

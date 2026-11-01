"""Synthetic geometry fixtures test graph extraction and source-level learning guards."""
import json
from pathlib import Path
import tempfile
import unittest
from component_graph import build_graph
from relation_prior_train import fit, run, summarize


def make_graph(gap, n=3):
    boxes = [
        {"min":[0,0,0],"max":[1,.8,.6],"triangles":450},
        {"min":[1+gap,0,0],"max":[1.4+gap,.6,.5],"triangles":120},
        {"min":[.2,1.0,0],"max":[.5,1.3,.4],"triangles":100},
    ]
    return build_graph(boxes[:n],[-.1,-.1,-.1],[2.5,2.5,2.5])


def sample_study(n=8):
    assets=[]
    for i in range(n):
        graph=make_graph(.01+i*.014 if i%2 else -.1)
        assets.append({
            "id":f"model{i}","license":"CC0-1.0",
            "mesh_analysis":"blender_geometry_inspected",
            "geometry":{"source_sha256":f"{i+1:064x}",
                        "component_graph":graph}
        })
    return {"schema":"assetwright-cc0-shape-study-v1","cycle":4,"assets":assets}


class ComponentGraphTests(unittest.TestCase):
    def test_spatial_relationships_and_no_names_or_vertices(self):
        graph=make_graph(.04)
        self.assertEqual(graph["schema"],"assetwright-component-graph-v1")
        self.assertEqual(graph["part_count"],3)
        self.assertEqual(graph["pair_count"],3)
        self.assertEqual(sum(graph["relation_counts"].values()),3)
        rels={e["relation"] for e in graph["edges"]}
        self.assertIn("near_bounds",rels)
        self.assertIn("separate_bounds",rels)
        self.assertEqual(len(summarize(graph)),8)
        self.assertNotIn("vertices",str(graph))
        self.assertNotIn("wheel",str(graph))

    def test_touching_aabbs_is_not_semantic_attachment(self):
        graph=make_graph(0)
        self.assertIn("overlapping_bounds",graph["relation_counts"])
        self.assertIn("not a verified joint",graph["note"])

    def test_invalid_edges_are_rejected(self):
        graph=make_graph(.02)
        graph["edges"][0]["a"]=999
        with self.assertRaises(ValueError):
            summarize(graph)

    def test_single_mesh_is_not_sufficient_for_relationship_training(self):
        graph=make_graph(.2,n=1)
        with self.assertRaises(ValueError):
            summarize(graph)
        report,model=fit({"schema":"assetwright-cc0-shape-study-v1","cycle":4,
                          "assets":[{"id":"one","license":"CC0-1.0",
                                     "mesh_analysis":"blender_geometry_inspected",
                                     "geometry":{"source_sha256":"a"*64,
                                                 "component_graph":graph}}]})
        self.assertEqual(report["status"],"insufficient_multi_part_data")
        self.assertIsNone(model)

    def test_source_disjoint_training_and_validation(self):
        report,model=fit(sample_study(8))
        self.assertEqual(report["licensed_multi_part_models"],8)
        self.assertEqual(report["train_models"],6)
        self.assertEqual(report["holdout_models"],2)
        self.assertEqual(len(model["centroids"][0]),8)
        self.assertFalse(model["android_deployable"])

    def test_model_only_written_when_enough_real_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            src=root/"source.json"
            src.write_text(json.dumps(sample_study(3)),encoding="utf-8")
            result=run(src,root/"train")
            self.assertEqual(result["status"],"insufficient_multi_part_data")
            self.assertFalse((root/"train"/"candidate_layout.json").exists())
            src.write_text(json.dumps(sample_study(8)),encoding="utf-8")
            result=run(src,root/"run2")
            self.assertTrue((root/"run2"/"evaluation.json").exists())
            self.assertTrue((root/"run2"/"candidate_layout.json").exists())
            self.assertEqual((root/"run2"/"validated_layout.json").exists(),
                             result["status"]=="trained_passed_validation")


if __name__=="__main__":
    unittest.main()

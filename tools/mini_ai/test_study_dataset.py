"""No raw meshes, duplicated source models, or private prompts in study history."""
import json
from pathlib import Path
import tempfile
import unittest

from component_graph import build_graph
from study_dataset import merge


def record(index: int, graph: bool = True):
    geometry = {
        "source_sha256": f"{index:064x}",
        "schema": "assetwright-geometry-descriptor-v1",
        "features": [0.15, 0.27, 0.02, 0.01, 0.2, 0.65, 0.09, 0.01],
        "unneeded_original_path": "/private/downloaded/model.blend",
    }
    if graph:
        geometry["component_graph"] = build_graph([
            {"min":[0,0,0],"max":[1,1,1],"triangles":100},
            {"min":[.9,1.0,0],"max":[1.3,1.2,.6],"triangles":60}
        ], [0,0,0], [2,2,2])
    return {
        "id": "asset"+str(index), "license": "CC0-1.0",
        "source_page":f"https://polyhaven.com/a/asset{index}",
        "mesh_analysis":"blender_geometry_inspected",
        "geometry":geometry, "unneeded_prompt":"private info"
    }


class StudyDatasetTests(unittest.TestCase):
    def test_deduplicate_sources_across_training_cycles(self):
        old={"schema":"assetwright-cc0-shape-study-v1","cycle":4,
             "assets":[record(1),record(2)]}
        new={"schema":"assetwright-cc0-shape-study-v1","cycle":5,
             "assets":[record(2),record(3)]}
        result=merge(new,old)
        self.assertEqual(result["source_count"],3)
        self.assertEqual(result["cycles"],[4,5])
        self.assertEqual(result["attempted_ids"],["asset1","asset2","asset3"])
        self.assertTrue(all(a["license"]=="CC0-1.0" for a in result["assets"]))
        self.assertNotIn("unneeded_prompt",str(result))
        self.assertNotIn("unneeded_original_path",str(result))
        self.assertEqual(len(result["assets"][0]["geometry"]["component_graph"]["nodes"]),2)

    def test_missing_license_cannot_enter_training_set(self):
        study={"schema":"assetwright-cc0-shape-study-v1","cycle":5,
               "assets":[record(1),record(2)]}
        study["assets"][1]["license"]="UNKNOWN"
        self.assertEqual(merge(study)["source_count"],1)

    def test_invalid_source_hash_rejected(self):
        study={"schema":"assetwright-cc0-shape-study-v1","cycle":5,
               "assets":[record(1)]}
        study["assets"][0]["geometry"]["source_sha256"]="not sha256"
        self.assertEqual(merge(study)["source_count"],0)


if __name__=="__main__":
    unittest.main()

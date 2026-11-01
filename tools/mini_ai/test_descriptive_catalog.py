"""Offline tests for the CC0 description-to-geometry catalog."""
import json
from pathlib import Path
import tempfile
import unittest

from descriptive_catalog import build,axis_ratios
from semantic_reference_search import index,search
from description_shape_train import fit,rows_from_catalog


def asset(i:int,kind:str="car",valid=True)->dict:
    ratio=(.24,.73) if kind=="car" else (.72,.95)
    # API dimensions are source labels in mm, not constructed here in prod.
    dims=[round(ratio[0]*1000),round(ratio[1]*1000),1000]
    return {
      "type":2 if valid else 1,
      "name":kind+" model "+str(i),
      "description":("A low elongated aerodynamic vehicle body with a smooth metal roof and wide panels"
                     if kind=="car" else
                     "A rounded heavy industrial machinery fixture with broad body and square frame"),
      "tags":[kind,"metal","body" if kind=="car" else "frame"],
      "category":"Transport/Cars" if kind=="car" else "Industrial/Machines",
      "attributes":{"material":["metal"],"condition":"clean","hostile":"ignored"},
      "dimensions":dims
    }


class CaptionCorpusTests(unittest.TestCase):
    def test_catalog_captions_provenance_and_grounded_geometry_only(self):
        history={
          "schema":"assetwright-cc0-shape-study-v1",
          "assets":[{"id":"car_1","license":"CC0-1.0",
                     "mesh_analysis":"blender_geometry_inspected",
                     "geometry":{"source_sha256":"a"*64,"features":[.2]*8}}]
        }
        raw={"car_1":asset(1,"car"),"machine_1":asset(1,"machine"),
             "texture":asset(3,"car",valid=False)}
        corpus,report=build(raw,history)
        self.assertEqual(report["total_models"],2)
        self.assertEqual(report["with_descriptive_60_char_text"],2)
        self.assertEqual(report["with_published_dimensions"],2)
        self.assertEqual(report["with_verified_blender_geometry"],1)
        self.assertEqual(corpus["records"][0]["id"],"car_1")
        self.assertEqual(corpus["records"][0]["description_origin"],"publisher_metadata")
        self.assertNotIn("hostile",corpus["records"][0]["facets"])
        self.assertEqual(corpus["records"][0]["dimension_ratios"],[.24,.73])
        self.assertNotIn("verified_blender_geometry",corpus["records"][1])

    def test_dimensions_and_bad_source_metadata(self):
        self.assertIsNone(axis_ratios([1,0,5]))
        self.assertIsNone(axis_ratios([1,"2",3]))
        self.assertEqual(axis_ratios([2000,1000,500]),[.25,.5])
        bad={"../private":asset(1),
             "good":{**asset(2),"description":None},
             "evil":{**asset(3),"name":""}}
        corpus,report=build(bad)
        self.assertEqual(report["total_models"],1)
        self.assertEqual(corpus["records"][0]["description_quality"],"missing")

    def test_reference_search_uses_actual_text_not_invented_parts(self):
        raw={"car_"+str(i):asset(i,"car") for i in range(12)}
        raw.update({"machine_"+str(i):asset(i,"machine") for i in range(12)})
        corpus,_=build(raw)
        retriever=index(corpus["records"])
        found=search(retriever,"metal industrial heavy machinery fixture",top=3)
        self.assertEqual(len(found),3)
        self.assertTrue(all("machine" in x["name"] for x in found))
        self.assertTrue(all(x["source_page"].startswith("https://polyhaven.com/a/")
                            for x in found))

    def test_numeric_prior_trains_only_from_described_licensed_objects(self):
        raw={}
        for i in range(140):
            raw[f"car_{i:04d}"]=asset(i,"car")
            raw[f"machine_{i:04d}"]=asset(i,"machine")
        corpus,_=build(raw)
        results,model=fit(corpus)
        self.assertEqual(results["licensed_labeled_objects"],280)
        self.assertGreaterEqual(results["heldout_objects"],10)
        self.assertEqual(model["feature_buckets"],512)
        self.assertFalse(model["android_deployable"])
        self.assertEqual(results["status"],"trained_passed_validation")
        self.assertLess(results["candidate_mse"],results["baseline_mse"])

    def test_small_or_invalid_catalog_cannot_promote_fake_training(self):
        corpus,_=build({"car_1":asset(1,"car")})
        result,model=fit(corpus)
        self.assertEqual(result["status"],"insufficient_described_dimensions")
        self.assertIsNone(model)
        corpus["records"][0]["license"]="unknown"
        self.assertEqual(len(rows_from_catalog(corpus)),0)


if __name__=="__main__":
    unittest.main()

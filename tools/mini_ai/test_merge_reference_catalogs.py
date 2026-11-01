"""Object licensing and provenance preserved across merged description corpora."""
import unittest
from merge_reference_catalogs import combine
from semantic_reference_search import index,search


class CombinedCatalogTests(unittest.TestCase):
    def test_cc0_only_and_cap3d_attribution(self):
        poly={"schema":"assetwright-description-geometry-catalog-v1",
              "records":[{"id":"engine1","source":"Poly Haven","license":"CC0-1.0",
                          "name":"Engine","publisher_description":"Metal turbine",
                          "source_page":"https://polyhaven.com/a/engine1",
                          "category":"Industrial","tags":["motor"],"facets":{},
                          "dimension_ratios":[.3,.7]}]}
        obj={"schema":"assetwright-objaverse-verified-cc0-captions-v1",
             "records":[{"uid":"0"*32,"name":"Mechanical engine","object_license":"CC0-1.0",
                         "metadata_license":"ODC-BY-1.0",
                         "publisher_description":"Engine assembly",
                         "cap3d_generated_caption":"Metal motor with curved housing and a dark intake",
                         "cap3d_caption_license":"ODC-BY-1.0",
                         "cap3d_source":"https://huggingface.co/datasets/tiange/Cap3D",
                         "metadata_source":"https://huggingface.co/datasets/allenai/objaverse",
                         "tags":["motor","engine"]},
                        {"uid":"1"*32,"name":"Restricted model","object_license":"CC-BY-NC",
                         "metadata_license":"ODC-BY-1.0",
                         "cap3d_generated_caption":"Should not be indexed"}]}
        merged,coverage=combine(poly,obj)
        self.assertEqual(coverage["records_total"],2)
        self.assertEqual(coverage["objaverse_with_cap3d"],1)
        self.assertEqual(merged["records"][1]["caption_license"],"ODC-BY-1.0")
        self.assertNotIn("Should not be indexed",str(merged))
        matches=search(index(merged["records"]),"curved motor housing",top=2)
        self.assertEqual(matches[0]["id"],"objaverse_"+"0"*32)
        self.assertIn("model-generated",matches[0]["description_origin"])

    def test_mislabeled_generated_caption_fails_closed(self):
        poly={"schema":"assetwright-description-geometry-catalog-v1","records":[]}
        obj={"schema":"assetwright-objaverse-verified-cc0-captions-v1","records":[
            {"uid":"f"*32,"name":"Tool","object_license":"CC0-1.0",
             "metadata_license":"ODC-BY-1.0",
             "cap3d_generated_caption":"Metal machine with gears and levers",
             "cap3d_caption_license":"unknown"}]}
        merged,report=combine(poly,obj)
        self.assertEqual(report["records_total"],0)


if __name__=="__main__":
    unittest.main()

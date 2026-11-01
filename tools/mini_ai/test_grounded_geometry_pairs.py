import unittest
from grounded_geometry_pairs import match


def rec(id, sha="a"*64, *, verified=True):
    return {
        "id":id,"license":"CC0-1.0" if verified else "restricted",
        "mesh_analysis":"blender_geometry_inspected",
        "geometry":{"schema":"assetwright-geometry-descriptor-v1",
                    "source_sha256":sha,"features":[.12,.4,.02,.004,.35,.8,.03,.005],
                    "triangles":2400,"source_format":"blend",
                    "component_graph":{"schema":"assetwright-component-graph-v1","part_count":3}}
    }


def captions(*ids):
    return {"schema":"assetwright-description-geometry-catalog-v1",
            "records":[{"id":id,"source":"Poly Haven","license":"CC0-1.0",
                        "name":f"Original {id}",
                        "publisher_description":"An original mechanical fixture with a curved steel body and rotating components.",
                        "description_origin":"publisher_metadata",
                        "source_page":f"https://polyhaven.com/a/{id}"} for id in ids]}


class GroundedPairsTest(unittest.TestCase):
    def test_exact_object_id_and_mesh_hash_are_required(self):
        cat=captions("engine_A","engine_B","engine_C")
        history={"schema":"assetwright-cc0-shape-study-v1",
                 "assets":[rec("engine_A"),rec("wrong_id","b"*64),rec("engine_C","c"*64,verified=False)]}
        dataset,report=match(cat,history)
        self.assertEqual(report["verified_text_mesh_pairs"],1)
        row=dataset["pairs"][0]
        self.assertEqual(row["source_object_id"],"engine_A")
        self.assertEqual(row["source_mesh_sha256"],"a"*64)
        self.assertEqual(row["verified_component_roles"],[])
        self.assertEqual(row["semantic_part_labels_status"],"not_verified")
        self.assertEqual(report["with_verified_component_roles"],0)

    def test_ambiguous_source_id_and_duplicate_mesh_do_not_inflate_training(self):
        c=captions("item_a","item_b")
        history={"schema":"assetwright-cc0-shape-study-v1",
                 "assets":[rec("item_a","a"*64),rec("item_a","b"*64),rec("item_b","a"*64)]}
        _,report=match(c,history)
        self.assertEqual(report["verified_text_mesh_pairs"],1)
        history["assets"].append(rec("item_b","a"*64))
        _,report=match(c,history)
        self.assertEqual(report["verified_text_mesh_pairs"],1)

    def test_missing_mesh_features_or_publisher_description_is_rejected(self):
        cat=captions("mesh")
        cat["records"][0]["publisher_description"]=""
        history={"schema":"assetwright-cc0-shape-study-v1","assets":[rec("mesh")]}
        _,report=match(cat,history)
        self.assertEqual(report["verified_text_mesh_pairs"],0)
        cat["records"][0]["publisher_description"]="Long original metal fixture description"
        history["assets"][0]["geometry"]["features"]=[2.]*8
        _,report=match(cat,history)
        self.assertEqual(report["verified_text_mesh_pairs"],0)


if __name__=="__main__":
    unittest.main()

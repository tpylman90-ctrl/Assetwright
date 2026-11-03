"""A recipe becomes a measured cause/effect example only with real GLB lineage."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest
from technique_effect_audit import evaluate

CURRICULUM=Path(__file__).resolve().parents[2]/"training/curricula/vehicle_modeling_techniques.json"


def benchmark(*, effect:bool=True):
    rows=[]
    for j,name in enumerate(("racer_exposed","coupe_exposed","suv_hidden","suv_tucked")):
        for k,variant in enumerate(("baseline","sculpted_canopy","faired_mounts","integrated_aero")):
            metrics={"roof_crown_width_ratio":.37,
                     "mount_root_tip_taper_ratio":1.}
            if variant in ("sculpted_canopy","integrated_aero"):
                metrics["roof_crown_width_ratio"] = .7 if effect else .37
            if variant in ("faired_mounts","integrated_aero"):
                metrics["mount_root_tip_taper_ratio"] = 1.85 if effect else 1.
            rows.append({
                "case":name,"variant":variant,
                "source_sha256":f"{j*4+k+1:064x}",
                "passed":True,
                "score":.9,"design_proxy_metrics":metrics
            })
    return {"schema":"assetwright-generator-quality-loop-v1","candidates":rows}


class TechniqueEffectsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content=json.loads(CURRICULUM.read_text(encoding="utf-8"))

    def test_verified_contrast_assigns_effect_not_visual_approval(self):
        result=evaluate(self.content,benchmark())
        self.assertEqual(result["number_of_techniques"],5)
        self.assertEqual(result["techniques_with_measured_effect"],2)
        self.assertEqual(result["techniques_without_independent_measurement"],1)
        self.assertEqual(result["techniques_requiring_new_geometry"],2)
        self.assertEqual(result["automatically_approved_as_professional_art"],0)
        crown=result["techniques"][0]
        self.assertEqual(crown["outcome"],"measured_operation_effect")
        self.assertEqual(crown["positive_effects"],4)
        self.assertFalse(crown["approved_as_visual_training"])
        mount=result["techniques"][2]
        self.assertEqual(mount["outcome"],"measured_operation_effect")
        self.assertTrue(all(x["delta"]>=.25 for x in mount["contrasts"]))

    def test_unimproved_geometric_effect_is_not_a_learning_example(self):
        result=evaluate(self.content,benchmark(effect=False))
        self.assertEqual(result["techniques_with_measured_effect"],0)
        self.assertEqual(result["techniques"][0]["outcome"],"effect_not_demonstrated")

    def test_model_without_same_origin_hash_is_rejected(self):
        b=benchmark()
        b["candidates"][0]["source_sha256"]="invalid"
        with self.assertRaisesRegex(ValueError,"checksum"):
            evaluate(self.content,b)
        b=benchmark()
        b["candidates"].append(copy.deepcopy(b["candidates"][0]))
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            evaluate(self.content,b)

    def test_failing_structural_candidate_does_not_teach_positive_effect(self):
        b=benchmark()
        for row in b["candidates"]:
            if row["variant"]=="faired_mounts":
                row["passed"]=False
        result=evaluate(self.content,b)
        self.assertEqual(result["techniques"][2]["outcome"],"effect_not_demonstrated")


if __name__=="__main__":
    unittest.main()

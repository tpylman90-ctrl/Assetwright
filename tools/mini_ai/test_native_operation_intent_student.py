"""Safety and held-out intent generalization tests for OUR native operator learner."""
import math
import unittest
from native_operation_intent_student import (
    SCHEMA,OPERATIONS,examples,text_features,train,evaluate,infer,init
)

class OwnedNativeOperatorIntentTests(unittest.TestCase):
    def test_original_authored_training_and_heldout_templates_are_disjoint(self):
        a,b=examples("train"),examples("holdout")
        self.assertEqual(len(a),135)
        self.assertEqual(len(b),36)
        self.assertFalse({x["prompt"] for x in a}&{x["prompt"] for x in b})
        self.assertFalse({x["source_group"] for x in a}&{x["source_group"] for x in b})
        self.assertTrue(all(x["source_kind"]=="authored_native_operation_recipe" for x in a+b))
        self.assertEqual({x["operation"] for x in a},set(OPERATIONS))
        self.assertEqual({x["strength"] for x in a},{.30,.60,.90})
    def test_native_student_independent_of_any_other_runtime_model(self):
        m=train(examples("train"),epochs=125)
        self.assertEqual(m["schema"],SCHEMA)
        self.assertFalse(m["inference_requires_teacher"])
        self.assertFalse(m["external_mesh_used"])
        self.assertFalse(m["android_deployable"])
        report=evaluate(m,examples("holdout"))
        self.assertGreaterEqual(report["heldout_accuracy"],.85)
        self.assertLess(report["heldout_strength_mae"],.105)
        self.assertEqual(report["status"],"validated_research_intent_student")
        self.assertFalse(report["template_group_overlap"])
        self.assertTrue(report["trained_model_creates_no_mesh"])
    def test_abstains_on_unfamiliar_requests_and_refuses_bad_checkpoint(self):
        m=init()
        vague=infer(m,"Please design this object")
        self.assertEqual(vague["status"],"abstain")
        m["external_mesh_used"]=True
        with self.assertRaisesRegex(ValueError,"Untrusted"):infer(m,"Please design this object")
    def test_predicted_native_strengths_are_bounded(self):
        m=train(examples("train"),epochs=125)
        for row in examples("holdout"):
            p=infer(m,row["prompt"])
            if p["status"]!="abstain":
                self.assertIn(p["operation"],OPERATIONS)
                self.assertTrue(math.isfinite(p["strength"]))
                self.assertTrue(0<=p["strength"]<=1)

if __name__=="__main__":unittest.main()

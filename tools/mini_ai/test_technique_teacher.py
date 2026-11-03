"""Verify direct procedural teaching with held-out authored critique prompts."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest

from technique_teacher import train,validate,predict,run

SOURCE=Path(__file__).resolve().parents[2]/"training/curricula/vehicle_modeling_techniques.json"


class TechniqueTeacherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.curriculum=json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_can_explain_real_modeling_operation_and_code_location(self):
        procedures=validate(self.curriculum)
        self.assertEqual(len(procedures),5)
        executable=[p for p in procedures if p["execution_status"]=="experimental_native_control"]
        self.assertEqual(len(executable),3)
        for p in executable:
            self.assertTrue((SOURCE.parents[2]/p["source_code"]).is_file())
            self.assertGreaterEqual(len(p["geometry_recipe"]),3)
            self.assertGreaterEqual(len(p["feedback_examples"]),8)
            self.assertGreaterEqual(len(p["holdout_feedback"]),3)
        planned=[p for p in procedures if p["execution_status"]=="requires_new_geometry_primitive"]
        self.assertEqual(len(planned),2)
        self.assertTrue(all(p["control"] is None for p in planned))

    def test_train_on_original_teacher_critique_and_holdout(self):
        report,policy=train(self.curriculum)
        self.assertEqual(report["status"],"technique_selector_validated")
        self.assertEqual(report["original_training_feedback"],36)
        self.assertEqual(report["heldout_feedback"],12)
        self.assertGreaterEqual(report["heldout_accuracy"],.75)
        self.assertEqual(policy["classes"],[
            "crown_profile_loft","shoulder_contour_loft","tapered_bracket_sections"])
        self.assertFalse(policy["auto_execute"])
        self.assertFalse(policy["trained_on_private_user_assets"])
        crown,gap=predict(policy,"This racing windshield looks like a giant bubble.")
        self.assertEqual(crown,"crown_profile_loft")
        self.assertGreater(gap,0)

    def test_unsupported_controls_and_primitive_forgery_rejected(self):
        raw=copy.deepcopy(self.curriculum)
        raw["techniques"][0]["control"]="exec_any_python"
        with self.assertRaisesRegex(ValueError,"controlled operation"):
            validate(raw)
        raw=copy.deepcopy(self.curriculum)
        raw["techniques"][3]["value"]=1.
        with self.assertRaisesRegex(ValueError,"Unimplemented operation"):
            validate(raw)

    def test_no_intent_returns_no_proposed_operation(self):
        _,model=train(self.curriculum)
        found,_=predict(model,"wxyzqfpl jnqrttzz")
        self.assertIsNone(found)

    def test_validation_is_required_before_writing_operation_policy(self):
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/"source.json"
            output=Path(root)/"output"
            source.write_text(json.dumps(self.curriculum),encoding="utf-8")
            result=run(source,output)
            self.assertEqual(result["status"],"technique_selector_validated")
            self.assertTrue((output/"validated_selector.json").is_file())
            self.assertTrue((output/"evaluation.json").is_file())
            tampered=copy.deepcopy(self.curriculum)
            for x in tampered["techniques"][:3]:
                x["holdout_feedback"]=[
                    "The green triangle has a connector and shape",
                    "A green triangle needs a connector and shape",
                    "The shape triangle has a green connector"
                ]
            source.write_text(json.dumps(tampered),encoding="utf-8")
            result=run(source,output)
            self.assertNotEqual(result["status"],"technique_selector_validated")
            # Validation failure must not leave an old "validated" file behind.
            # The production tool should avoid implying a stale policy passed.
            self.assertFalse((output/"validated_selector.json").is_file())


if __name__=="__main__":
    unittest.main()

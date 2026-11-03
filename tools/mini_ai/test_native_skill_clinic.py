"""Clinic safeguards: reviewed errors, replay, no leakage, no pseudo-labels."""
import hashlib
import json
from pathlib import Path
import unittest

from native_operation_intent_student import examples,train,SCHEMA
from native_skill_clinic import (
    SCHEMA as CLINIC, CURRICULUM, PROOF, digest, practise,
    validate_curriculum, validate_proof, validate_model, evaluate_rows,
    unresolved_review_gaps,
)

class NativeMistakeClinicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=train(examples("train"),epochs=125)
        cls.curriculum=json.loads((Path(__file__).resolve().parents[2]/
                "training/curricula/native_skill_clinic_v1.json").read_text())
        cls.phases=validate_curriculum(cls.curriculum)
    def test_three_phases_have_different_templates_and_multiple_strengths(self):
        groups={phase:{x["source_group"] for x in rows}
                for phase,rows in self.phases.items()}
        self.assertEqual(len(self.phases["correction"]),90)
        self.assertEqual(len(self.phases["development"]),27)
        self.assertEqual(len(self.phases["blind"]),27)
        self.assertFalse(groups["correction"]&groups["development"])
        self.assertFalse(groups["correction"]&groups["blind"])
        self.assertFalse(groups["development"]&groups["blind"])
        self.assertTrue(all(x["source_kind"]=="explicit_native_gold_label"
                            for rows in self.phases.values() for x in rows))
    def test_disallows_self_taught_and_malformed_review_prompts(self):
        altered=json.loads(json.dumps(self.curriculum))
        altered["blind"][0]["template"]=altered["correction"][0]["template"]
        with self.assertRaisesRegex(ValueError,"disjoint"):
            validate_curriculum(altered)
        altered=json.loads(json.dumps(self.curriculum))
        altered["correction"][0]["operation"]="download_external_teacher_mesh"
        with self.assertRaisesRegex(ValueError,"Unknown native"):
            validate_curriculum(altered)
        altered=json.loads(json.dumps(self.curriculum))
        altered["license"]="unverified"
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            validate_curriculum(altered)
    def test_requires_actual_native_GLBS_and_matching_weights(self):
        data=json.dumps(self.model).encode()
        report={"schema":"assetwright-native-operator-intent-evaluation-v1",
                "status":"validated_research_intent_student",
                "template_group_overlap":False,"heldout_accuracy":1.}
        proof={"schema":PROOF,"passed":True,
               "checks":{str(i):True for i in range(12)},
               "research_checkpoint_sha256":hashlib.sha256(data).hexdigest()}
        validate_proof(proof,data,report)
        with self.assertRaisesRegex(ValueError,"hash-matched"):
            validate_proof({**proof,"research_checkpoint_sha256":"0"*64},data,report)
        with self.assertRaisesRegex(ValueError,"hash-matched"):
            validate_proof({**proof,"checks":{**proof["checks"],"4":False}},data,report)
    def test_negative_visual_reviews_are_not_falsely_taught_as_gold(self):
        sample={"schema":"assetwright-original-glb-visual-review-v1",
                "review_status":"negative_design_references_only",
                "reviews":[{"allowed_for_training":False,
                            "human_final_approval":False,
                            "observations":["cockpit-to-hull transition disconnected",
                                            "rear engines look mounted rather than integrated"]}]}
        critique=unresolved_review_gaps(sample)
        self.assertEqual(critique["used_as_positive_training_labels"],0)
        self.assertEqual(critique["reviewed_negative_examples"],1)
        sample["reviews"][0]["allowed_for_training"]=True
        with self.assertRaisesRegex(ValueError,"human approval"):
            unresolved_review_gaps(sample)

    def test_continuation_preserves_owned_weights_and_rehearses_prior_learning(self):
        validate_model(self.model)
        stage,metrics=practise(self.model,
                self.phases["correction"],self.phases["development"],
                examples("holdout"),epochs=12)
        self.assertEqual(stage["schema"],SCHEMA)
        self.assertFalse(stage["external_mesh_used"])
        self.assertFalse(stage["android_deployable"])
        self.assertGreater(metrics["rehearsal_lessons"],100)
        self.assertGreater(metrics["training_updates"],0)
        self.assertEqual(len(stage["class_weights"]),3)
        old=evaluate_rows(self.model,examples("holdout"))
        new=evaluate_rows(stage,examples("holdout"))
        self.assertGreaterEqual(new["operator_accuracy"],
                                old["operator_accuracy"]-.03)
        self.assertLessEqual(new["strength_mae_all"],
                             old["strength_mae_all"]+.025)

if __name__=="__main__":unittest.main()

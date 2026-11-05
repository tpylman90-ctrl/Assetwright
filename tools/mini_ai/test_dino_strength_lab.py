"""Source-disjoint multi-session geometry strength and release guards."""
import hashlib
import math
import os
import unittest

from advanced_form_student import OPERATIONS
from dino_delta_school import (FAMILIES,LEVELS,STUDY,
                               expected_changes,BASELINES,EXPECTED)
from dino_strength_acceptance import reconcile
from dino_strength_student import SEEDS,EPOCHS,SCHEMA,RESULT_SCHEMA


def evidence(success=False):
    accuracy=.78 if success else .52
    guided_mae=.125 if success else .235
    teacherfree_mae=.15 if success else .241
    errs=(teacherfree_mae-guided_mae)/teacherfree_mae
    source=[]
    for family in FAMILIES["validation"]:
        for op in OPERATIONS:
            for level in LEVELS["validation"]:
                case="__".join(("validation",family,op.lower(),
                               "s%03d"%round(level*1000)))
                digest=hashlib.sha256(case.encode()).hexdigest()
                source.append({
                    "case":case,"family":family,"target_operation":op,
                    "target_strength":level,"source_glb_sha256":digest,
                    "DINO_guided":{"strength":level,
                                   "correct_operation":True},
                    "teacher_free":{"strength":level}
                })
    digest=hashlib.sha256("\n".join(sorted(
        x["source_glb_sha256"] for x in source)).encode()).hexdigest()
    per={op:{"total":16,"strength_mae":guided_mae} for op in OPERATIONS}
    visual={
        "schema":RESULT_SCHEMA,
        "training_examples":756,"development_examples":96,
        "untouched_validation_examples":96,
        "independent_seeds_per_condition":8,
        "total_independent_training_sessions":16,
        "source_modified_sha256_validation":digest,
        "teacher_used_during_inference":False,
        "external_AI_produces_3d":False,
        "DINO_strength_error_reduction_fraction":errs,
        "heldout":{
            "teacher_free":{"accuracy":accuracy-.01,"strength_mae":teacherfree_mae},
            "DINO_guided":{"accuracy":accuracy,"strength_mae":guided_mae,
                           "per_operator":per}
        }
    }
    forward={
        "schema":"assetwright-native-before-after-forward-audit-v1",
        "study_id":"strength_v2",
        "fresh_original_target_glbs":96,
        "real_student_generated_glbs":192,
        "native_unmodified_family_baselines":4,
        "all_native_glbs_structurally_audited":True,
        "external_AI_used_to_generate_meshes":False,
        "source_hashes_sha256":digest,
        "paired_teacher_free":{
            "operation_accuracy":accuracy-.01,"strength_mae":teacherfree_mae},
        "paired_with_DINO":{
            "operation_accuracy":accuracy,"strength_mae":guided_mae},
        "improvement_over_unchanged_native_fraction":.22 if success else .04,
        "DINO_improvement_over_paired_without_teacher_fraction":.045 if success else .003,
        "cases":source
    }
    checkpoint={
        "schema":SCHEMA,
        "source_hash_validation":digest,
        "owned_generator":"AssetWright-Kotlin-AdvancedFormLab",
        "teacher_needed_at_inference":False,
        "android_deployable":False,
        "approved_for_geometry_generation":False,
        "supported_operations":list(OPERATIONS)
    }
    return visual,forward,checkpoint


@unittest.skipUnless(os.getenv("ASSETWRIGHT_DINO_STUDY")=="strength_v2",
                     "Fresh strength experiment has separate source configuration")
class NativeStrengthCalibrationTests(unittest.TestCase):
    def test_new_cad_curriculum_and_sixteen_real_training_sessions(self):
        self.assertEqual(STUDY,"strength_v2")
        self.assertEqual(EXPECTED,948)
        self.assertEqual(BASELINES,26)
        self.assertEqual(len(expected_changes()),948)
        self.assertEqual(len(SEEDS),8)
        self.assertEqual(len(set(SEEDS)),8)
        self.assertGreaterEqual(EPOCHS,150)
        for phase,n in (("train",756),("development",96),("validation",96)):
            self.assertEqual(sum(identity[0]==phase
                                 for identity in expected_changes().values()),n)
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))
        self.assertFalse(any(f.startswith("bdhold") for f in FAMILIES["validation"]))

    def test_underperforming_study_remains_research_only(self):
        result=reconcile(*evidence(False))
        self.assertEqual(result["status"],"research_candidate_not_approved")
        self.assertFalse(result["automatic_promotion"])
        self.assertFalse(result["checks"]["continuous_strength_MAE_le_0_18"])

    def test_even_passing_numbers_require_human_review(self):
        result=reconcile(*evidence(True))
        self.assertEqual(result["status"],"eligible_for_human_research_review")
        self.assertFalse(result["Android_deployable"])
        self.assertTrue(result["human_visual_review_required"])

    def test_source_hash_and_forward_metrics_must_agree(self):
        a,b,c=evidence(True)
        b["source_hashes_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"Mismatch"):
            reconcile(a,b,c)
        a,b,c=evidence(True)
        b["paired_with_DINO"]["strength_mae"]+=.05
        with self.assertRaisesRegex(ValueError,"disagree"):
            reconcile(a,b,c)

    def test_teacher_is_not_a_3d_generator_or_inference_runtime(self):
        a,b,c=evidence(True)
        c["teacher_needed_at_inference"]=True
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            reconcile(a,b,c)
        a,b,c=evidence(True)
        b["external_AI_used_to_generate_meshes"]=True
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            reconcile(a,b,c)

    def test_per_operation_and_monotonicity_gates_cannot_be_skipped(self):
        a,b,c=evidence(True)
        a["heldout"]["DINO_guided"]["per_operator"]["SECTION_TWIST"]["strength_mae"]=.42
        self.assertEqual(reconcile(a,b,c)["status"],"research_candidate_not_approved")
        a,b,c=evidence(True)
        for row in b["cases"]:
            row["DINO_guided"]["strength"]=1.0-row["target_strength"]
        result=reconcile(a,b,c)
        self.assertFalse(result["checks"]["monotonic_strength_consistency"])


if __name__=="__main__":
    unittest.main()

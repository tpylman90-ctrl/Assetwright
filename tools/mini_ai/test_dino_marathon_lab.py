"""Offline strict source partition and 32-minute native research promotion tests."""
import hashlib
import os
import unittest

from advanced_form_student import OPERATIONS
from dino_delta_school import FAMILIES,LEVELS,STUDY,BASELINES,EXPECTED,expected_changes
from dino_marathon_student import SEEDS,STUDENT_SCHEMA,EVALUATION_SCHEMA
from dino_marathon_acceptance import reconcile


def fixture(success=True):
    examples=[]
    for family in FAMILIES["validation"]:
        for operation in OPERATIONS:
            for strength in LEVELS["validation"]:
                case=f"validation__{family}__{operation.lower()}__s{round(strength*1000):03d}"
                sha=hashlib.sha256(case.encode()).hexdigest()
                examples.append({
                    "case":case,"family":family,
                    "target_operation":operation,
                    "target_strength":strength,
                    "source_glb_sha256":sha,
                    "DINO_guided":{"strength":strength},
                    "teacher_free":{"strength":strength}
                })
    digest=hashlib.sha256("\n".join(sorted(
        r["source_glb_sha256"] for r in examples)).encode()).hexdigest()
    time_per_session=120.5
    history={
        mode:[{
            "seed":seed,"session_training_elapsed_seconds":time_per_session,
            "selected_dev_step":70,"optimizer_updates":140,
        } for seed in SEEDS]
        for mode in ("teacher_free","DINO_guided")
    }
    history.update({"teacher_free_winner_seed":SEEDS[0],
                    "DINO_guided_winner_seed":SEEDS[2]})
    pure_acc=.73;guided_acc=.81
    pure_mae=.156;guided_mae=.128
    visual={
        "schema":EVALUATION_SCHEMA,
        "original_meshes":888,
        "original_before_after_changes":864,
        "train_examples":672,"development_examples":96,
        "untouched_holdout_examples":96,
        "independent_seeds_per_condition":8,
        "completed_independent_training_sessions":16,
        "requested_active_training_seconds":1920,
        "verified_active_training_seconds":1928,
        "all_session_development_results":history,
        "source_validation_hashes_sha256":digest,
        "teacher_strength_gain_fraction":(pure_mae-guided_mae)/pure_mae,
        "teacher_generates_geometry":False,
        "teacher_needed_at_inference":False,
        "heldout":{
            "teacher_free":{"accuracy":pure_acc,"strength_mae":pure_mae},
            "DINO_guided":{"accuracy":guided_acc,"strength_mae":guided_mae,
                          "per_operation":{
                              name:{"total":16,"strength_mae":.13}
                              for name in OPERATIONS}}
        }
    }
    geo={
        "schema":"assetwright-native-before-after-forward-audit-v1",
        "study_id":"strength_marathon_v3",
        "fresh_original_target_glbs":96,
        "real_student_generated_glbs":192,
        "native_unmodified_family_baselines":4,
        "all_native_glbs_structurally_audited":True,
        "external_AI_used_to_generate_meshes":False,
        "source_hashes_sha256":digest,
        "paired_teacher_free":{"operation_accuracy":pure_acc,
                               "strength_mae":pure_mae},
        "paired_with_DINO":{"operation_accuracy":guided_acc,
                            "strength_mae":guided_mae},
        "improvement_over_unchanged_native_fraction":.24 if success else .01,
        "DINO_improvement_over_paired_without_teacher_fraction":.04 if success else -.01,
        "cases":examples
    }
    student={
        "schema":STUDENT_SCHEMA,
        "original_native_generator":"AssetWright-Kotlin-AdvancedFormLab",
        "teacher_needed_at_inference":False,
        "teacher_generates_geometry":False,
        "android_deployable":False,
        "approved_for_generation":False,
        "blind_source_hashes_sha256":digest,
        "supported_ops":list(OPERATIONS),
    }
    return visual,geo,student


@unittest.skipUnless(os.getenv("ASSETWRIGHT_DINO_STUDY")=="strength_marathon_v3",
                     "Marathon tests need explicit new source partition")
class MarathonIntegrityTests(unittest.TestCase):
    def test_protected_new_strength_families(self):
        self.assertEqual(STUDY,"strength_marathon_v3")
        self.assertEqual(BASELINES,24)
        self.assertEqual(EXPECTED,864)
        self.assertEqual(len(expected_changes()),864)
        self.assertEqual(len(SEEDS),8)
        self.assertEqual(len(set(SEEDS)),8)
        for phase,n in (("train",672),("development",96),("validation",96)):
            self.assertEqual(sum(item[0]==phase
                                 for item in expected_changes().values()),n)
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))
        self.assertTrue(all(name.startswith("bm_blind")
                            for name in FAMILIES["validation"]))
        self.assertFalse(set(FAMILIES["validation"])&
                         {"bs_blind01","bdhold01"})

    def test_approves_only_eligible_for_human_research_review(self):
        r=reconcile(*fixture(True))
        self.assertEqual(r["status"],"eligible_for_human_research_review")
        self.assertFalse(r["never_auto_deploy_to_Android"] is False)
        self.assertTrue(r["human_visual_approval_required"])

    def test_underperforming_mesh_reconstructions_are_rejected(self):
        r=reconcile(*fixture(False))
        self.assertEqual(r["status"],"research_candidate_rejected")
        self.assertFalse(r["checks"]["native_geometry_beats_unmodified_by_10pct"])

    def test_real_30_minute_optimization_must_be_proven(self):
        a,b,c=fixture()
        a["verified_active_training_seconds"]=900
        with self.assertRaisesRegex(ValueError,"optimization time"):
            reconcile(a,b,c)
        a,b,c=fixture()
        a["all_session_development_results"]["DINO_guided"].pop()
        with self.assertRaisesRegex(ValueError,"gradient-optimization"):
            reconcile(a,b,c)

    def test_real_GLBS_hashes_match_student_heldout(self):
        a,b,c=fixture()
        b["source_hashes_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"mismatch"):
            reconcile(a,b,c)
        a,b,c=fixture()
        b["paired_with_DINO"]["strength_mae"]+=.03
        with self.assertRaisesRegex(ValueError,"contradicts"):
            reconcile(a,b,c)

    def test_reverse_stronger_transformations_fail_monotonic_gate(self):
        a,b,c=fixture()
        for row in b["cases"]:
            row["DINO_guided"]["strength"]=1-row["target_strength"]
        result=reconcile(a,b,c)
        self.assertFalse(result["checks"]["monotonic_strength_violations_le_four"])

    def test_frozen_teacher_cannot_generate_or_ship_models(self):
        a,b,c=fixture()
        c["teacher_needed_at_inference"]=True
        with self.assertRaisesRegex(ValueError,"safety boundary"):
            reconcile(a,b,c)
        a,b,c=fixture()
        b["external_AI_used_to_generate_meshes"]=True
        with self.assertRaisesRegex(ValueError,"safety boundary"):
            reconcile(a,b,c)


if __name__=="__main__":
    unittest.main()

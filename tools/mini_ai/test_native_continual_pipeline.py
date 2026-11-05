"""Offline proof that cumulative model learning does not become fake promotion."""
import hashlib
import os
import unittest

from advanced_form_student import OPERATIONS
from dino_delta_school import STUDY,FAMILIES,LEVELS,EXPECTED,BASELINES,expected_changes
from native_continual_student import SCHEMA,MODEL_SCHEMA,SEEDS,MODES
from native_continual_forward_audit import RESULT
from native_continual_acceptance import assess


def fake_improvement(pass_gain=True):
    prior_rmse=.008
    new_rmse=.0077 if pass_gain else .0092
    labels=[]
    for family in FAMILIES["validation"]:
        for op in OPERATIONS:
            for strength in LEVELS["validation"]:
                case=f"validation__{family}__{op.lower()}__s{round(strength*1000):03d}"
                labels.append({
                    "case":case,"family":family,
                    "source_sha256":hashlib.sha256(case.encode()).hexdigest(),
                })
    digest=hashlib.sha256("\n".join(sorted(
        case["source_sha256"] for case in labels)).encode()).hexdigest()
    sessions=[]
    for mode in MODES:
        for seed in SEEDS:
            sessions.append({
                "seed":seed,"mode":mode,
                "optimizer_updates":4000,
                "active_training_seconds":241.,
                "selected_on_new_development_only":True
            })
    results={
        "schema":SCHEMA,"study":"strength_continual_v4",
        "prior_training_sources_rehearsed":672,
        "new_training_examples":504,
        "new_development_examples":96,
        "new_unseen_validation_examples":96,
        "prior_development_retention_examples":96,
        "historical_validation_leaked_into_training":False,
        "training_sessions_completed":8,
        "old_prior_saved_hash":"f"*64,
        "warm_start_verified_from_original":True,
        "rebased_max_logit_difference":.00005,
        "measured_training_seconds":1928,
        "configured_training_seconds":1920,
        "teacher_used_in_this_training":False,
        "external_AI_created_meshes":False,
        "automatic_production_promotion":False,
        "sessions":sessions,
        "new_blind_original_mesh_hash":digest,
        "old_train_prior":{"accuracy":.98,"strength_mae":.07},
        "old_train_candidate":{"accuracy":.978,"strength_mae":.075},
        "new_blind":{
            "prior":{"accuracy":.75,"strength_mae":.18},
            "continued":{"accuracy":.81,"strength_mae":.15}
        }
    }
    geometry={
        "schema":RESULT,"study_id":"strength_continual_v4",
        "fresh_original_geometry_count":96,
        "reconstructed_original_geometry_count":192,
        "independent_family_count":4,
        "all_GLBS_structurally_valid":True,
        "no_outside_3d":True,
        "blinded_source_hashes_digest":digest,
        "prior":{"operation_accuracy":.75,"strength_mae":.18,
                 "normalized_vertex_rmse":prior_rmse},
        "continued":{"operation_accuracy":.81,"strength_mae":.15,
                     "normalized_vertex_rmse":new_rmse},
        "continued_geometry_gain_vs_frozen_parent_fraction":(
            prior_rmse-new_rmse)/prior_rmse,
        "unchanged_source_normalized_vertex_rmse":.017,
        "cases":labels
    }
    model={
        "schema":MODEL_SCHEMA,
        "parent_source_checkpoint_sha256":"f"*64,
        "previous_stored_model_reloaded":True,
        "old_training_replay_samples":672,
        "fresh_new_training_samples":504,
        "selected_on_fresh_development_only":True,
        "fresh_validation_hash":digest,
        "teacher_required_at_inference":False,
        "android_deployable":False,
        "human_review_required":True
    }
    return results,geometry,model


@unittest.skipUnless(os.getenv("ASSETWRIGHT_DINO_STUDY")=="strength_continual_v4",
                     "v4 tests require new independently partitioned cohort")
class GenuineContinualLearningTests(unittest.TestCase):
    def test_unseen_native_families_are_not_old_inspected_holdouts(self):
        self.assertEqual(STUDY,"strength_continual_v4")
        self.assertEqual(EXPECTED,696)
        self.assertEqual(BASELINES,20)
        self.assertEqual(len(expected_changes()),696)
        self.assertEqual(len(SEEDS)*len(MODES),8)
        for phase,n in (("train",504),("development",96),("validation",96)):
            self.assertEqual(sum(v[0]==phase for v in expected_changes().values()),n)
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))
        self.assertTrue(all(f.startswith("bc_blind") for f in FAMILIES["validation"]))

    def test_valid_replay_and_native_GLBS_are_only_research_eligible(self):
        result=assess(*fake_improvement(True))
        self.assertEqual(result["status"],"eligible_for_human_research_review")
        self.assertFalse(result["android_installed"])
        self.assertTrue(result["parent_original_checkpoint_unchanged"])

    def test_worse_actual_GLBS_keep_old_weights(self):
        result=assess(*fake_improvement(False))
        self.assertEqual(result["status"],"candidate_not_promoted_parent_retained")
        self.assertFalse(result["checks"]["real_native_GLBS_at_least_2pct_better_than_parent"])

    def test_no_fake_continuation_without_persisted_weights_and_replay(self):
        a,b,c=fake_improvement()
        c["previous_stored_model_reloaded"]=False
        with self.assertRaisesRegex(ValueError,"original weight reuse"):
            assess(a,b,c)
        a,b,c=fake_improvement()
        a["prior_training_sources_rehearsed"]=0
        with self.assertRaisesRegex(ValueError,"incomplete"):
            assess(a,b,c)
        a,b,c=fake_improvement()
        a["historical_validation_leaked_into_training"]=True
        with self.assertRaisesRegex(ValueError,"incomplete"):
            assess(a,b,c)

    def test_blind_hashes_match_actual_forward_GLBS(self):
        a,b,c=fake_improvement()
        b["blinded_source_hashes_digest"]="0"*64
        with self.assertRaisesRegex(ValueError,"SHA mismatch"):
            assess(a,b,c)
        a,b,c=fake_improvement()
        b["continued"]["operation_accuracy"]+=.05
        with self.assertRaisesRegex(ValueError,"differ"):
            assess(a,b,c)

    def test_incomplete_training_or_mobile_unsafe_is_rejected(self):
        a,b,c=fake_improvement()
        a["measured_training_seconds"]=25
        with self.assertRaisesRegex(ValueError,"gradient training budget"):
            assess(a,b,c)
        a,b,c=fake_improvement()
        c["android_deployable"]=True
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            assess(a,b,c)

    def test_original_weight_rebase_is_verified_before_training(self):
        a,b,c=fake_improvement()
        a["rebased_max_logit_difference"]=.01
        with self.assertRaisesRegex(ValueError,"original weight reuse"):
            assess(a,b,c)


if __name__=="__main__":
    unittest.main()

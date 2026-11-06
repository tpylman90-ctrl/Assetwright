"""Truthful identity curriculum tests: old action weights frozen, 8 real forms."""
import hashlib
import os
import unittest

from dino_delta_school import STUDY,EXPECTED,BASELINES,FAMILIES,LEVELS,expected_changes
from native_shape_identity_student import (
    SCHEMA,MODEL_SCHEMA,CONDITIONS,VARIANTS,FORMS)
from native_shape_identity_forward_audit import SCHEMA as AUDIT
from native_shape_identity_acceptance import assess
from native_shape_identity_views import INPUT_DIM,SIDES


def synthetic(pass_geometry=True):
    actual=[]
    for family in FAMILIES["validation"]:
        shape=FORMS[1+(int(family[-2:])-1)%8]
        for op in (
            "SECTION_LOFT","TANGENT_SWEEP","SECTION_TWIST",
            "SUPERELLIPSE_PROFILE","LOWER_RECESS","RIBBED_FAIRING"):
            for strength in LEVELS["validation"]:
                case=f"validation__{family}__{op.lower()}__s{round(strength*1000):03d}"
                source_hash=hashlib.sha256(case.encode()).hexdigest()
                record={
                    "case":case,"family":family,"target_form":shape,
                    "target_operation":op,"target_strength":strength,
                    "original_glb_sha256":source_hash
                }
                for condition in VARIANTS:
                    record[condition]={
                        "form":shape,"operation":op,"strength":strength
                    }
                actual.append(record)
    assert len(actual)==384
    source_hash=hashlib.sha256("\n".join(sorted(
        r["original_glb_sha256"] for r in actual)).encode()).hexdigest()
    physical={}
    per={}
    for condition in VARIANTS:
        chosen=condition!="prior"
        physical[condition]={
            "form_accuracy":.5 if not chosen else .875,
            "predicted_distinct_archetypes":8,
            "predicted_unique_triangle_topologies":6,
            "generic_shell_output_count":0,
            "operation_accuracy":.9,
            "strength_mae":.12,
            "mean_3d_surface_chamfer":.030 if not chosen else (
                .009 if pass_geometry else .031),
            "per_form":{
                name:{"count":48,"correct_form":48 if chosen else 24}
                for name in FORMS[1:]
            }
        }
        per[condition]={
            "source_form_accuracy":physical[condition]["form_accuracy"],
            "predicted_unique_form_types":8
        }
    # Selected method's actual 3D GLB scores are not checkpoint selectors.
    audit={
        "schema":AUDIT,"study_id":"shape_identity_v7",
        "source_blind_native_shapes":384,
        "real_student_generated_GLBS":1536,
        "original_validation_families":16,
        "original_validation_archetypes":8,
        "source_hashes_sha256":source_hash,
        "external_meshes_used":False,
        "all_source_and_reconstructed_meshes_valid":True,
        "android_deployed":False,
        "unchanged_native_surface_chamfer":.015,
        "results":physical,
        "physical_3d_gain_vs_generic_parent":{
            name:(.030-physical[name]["mean_3d_surface_chamfer"])/.030
            for name in CONDITIONS
        },
        "individual_GLBS":actual
    }
    sessions=[
        {
            "condition":condition,"seed":seed,
            "actual_gradient_seconds":300.02,
            "updates":200,"selected_development_step":160
        } for condition in CONDITIONS for seed in (313,1601)
    ]
    report={
        "schema":SCHEMA,"study":"shape_identity_v7",
        "original_v6_experimental_parent_sha256":"d"*64,
        "old_model_research_gate":"research_not_promoted_legacy_checkpoint_retained",
        "original_operation_and_strength_weights_frozen":True,
        "training_unique_native_form_baselines":56,
        "new_training_unique_form_baselines":40,
        "previous_training_only_unique_form_baselines":16,
        "previous_v6_blind_used_in_training":False,
        "fresh_dev_unique_native_forms":16,
        "fresh_blind_unique_native_forms":16,
        "fresh_blind_new_native_transformations":384,
        "balanced_dimensions_across_all_eight_forms":True,
        "separate_32x32_baseline_three_view_encoder":True,
        "same_start_data_budget_all_conditions":True,
        "completed_independent_sessions":6,
        "no_pretrained_outside_AI":True,
        "android_neural_deployed":False,
        "optimizer_active_seconds":1800.12,"required_seconds":1800,
        "sessions":sessions,
        "development":{
            "three_view":{"selection_priority":.67},
            "contrastive_identity":{"selection_priority":.56},
            "hard_form_distinctions":{"selection_priority":.71}
        },
        "development_only_method_selected":"contrastive_identity",
        "new_blind_source_sha256":source_hash,
        "new_blind_form_results":per
    }
    lineage={
        "schema":MODEL_SCHEMA,
        "parent_source_weights_sha256":"d"*64,
        "old_operation_network_frozen":True,
        "android_approved":False,
        "identity_cameras":["side","front","top"],
        "identity_input_dim":3072,
        "parent_form_class_names":list(FORMS),
        "identity_input_mean":[0.]*3072,
        "identity_input_std":[1.]*3072,
        "chosen_on_new_development_only":"contrastive_identity",
        "fresh_blind_source_sha256":source_hash
    }
    return report,audit,lineage


@unittest.skipUnless(os.getenv("ASSETWRIGHT_DINO_STUDY")=="shape_identity_v7",
                     "Requires source-balanced new v7 curriculum")
class TestOriginalShapeIdentity(unittest.TestCase):
    def test_counterbalanced_sources_not_previous_blind(self):
        self.assertEqual(STUDY,"shape_identity_v7")
        self.assertEqual(EXPECTED,1968)
        self.assertEqual(BASELINES,72)
        self.assertEqual({k:len(v) for k,v in FAMILIES.items()},
                         {"train":40,"development":16,"validation":16})
        self.assertEqual({p:sum(row[0]==p for row in expected_changes().values())
                          for p in FAMILIES},
                         {"train":1200,"development":384,"validation":384})
        self.assertTrue(all(n.startswith("si_blind") for n in FAMILIES["validation"]))
        self.assertEqual(INPUT_DIM,3072)
        self.assertEqual(SIDES,("side","front","top"))

    def test_only_real_original_3d_and_eight_forms_qualify(self):
        verdict=assess(*synthetic())
        self.assertEqual(verdict["status"],"eligible_for_human_research_review")
        self.assertTrue(verdict["original_operation_network_frozen"])
        self.assertFalse(verdict["android_neural_deployed"])

    def test_chamfer_regression_rejects_non_generic_improvement_claim(self):
        verdict=assess(*synthetic(False))
        self.assertEqual(verdict["status"],"research_candidate_not_promoted")
        self.assertFalse(verdict["checks"][
            "source_aware_3d_surface_gain_vs_prior_at_least_12pct"])

    def test_identity_cannot_change_any_original_operation_or_strength(self):
        a,b,c=synthetic()
        b["individual_GLBS"][0]["contrastive_identity"]["strength"]+=.01
        with self.assertRaisesRegex(ValueError,"Frozen native operation"):
            assess(a,b,c)

    def test_blind_cannot_select_a_different_winner(self):
        a,b,c=synthetic()
        a["development_only_method_selected"]="hard_form_distinctions"
        with self.assertRaisesRegex(ValueError,"Blind data used"):
            assess(a,b,c)

    def test_heldout_original_source_hashes_and_full_1536_GLBS_required(self):
        a,b,c=synthetic()
        b["source_hashes_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"Source blind original"):
            assess(a,b,c)
        a,b,c=synthetic()
        a["previous_v6_blind_used_in_training"]=True
        with self.assertRaisesRegex(ValueError,"Missing independent"):
            assess(a,b,c)
        a,b,c=synthetic()
        a["original_operation_and_strength_weights_frozen"]=False
        with self.assertRaisesRegex(ValueError,"network changed"):
            assess(a,b,c)


if __name__=="__main__":
    unittest.main()

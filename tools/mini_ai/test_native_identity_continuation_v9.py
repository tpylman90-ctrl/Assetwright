"""Independent v9 native form learning and frozen-blind safety invariants."""
from __future__ import annotations
import hashlib
import os
import unittest

from dino_delta_school import STUDY,FAMILIES,LEVELS,EXPECTED,BASELINES,expected_changes
from native_identity_continuation_v9 import (
    SCHEMA,MODEL_SCHEMA,CONDITIONS,VARIANTS,FORMS,SEEDS)
from native_identity_continuation_forward_audit import SCHEMA as FORWARD
from native_identity_continuation_acceptance import assess


def fixture(good=True):
    rows=[]
    for family in FAMILIES["validation"]:
        archetype=FORMS[1+(int(family[-2:])-1)%8]
        for operation in (
            "SECTION_LOFT","TANGENT_SWEEP","SECTION_TWIST",
            "SUPERELLIPSE_PROFILE","LOWER_RECESS","RIBBED_FAIRING"):
            for strength in LEVELS["validation"]:
                case=f"validation__{family}__{operation.lower()}__s{round(strength*1000):03d}"
                item={
                    "case":case,"family":family,
                    "target_form":archetype,
                    "target_operation":operation,
                    "target_strength":strength,
                    "original_glb_sha256":hashlib.sha256(case.encode()).hexdigest()
                }
                for name in VARIANTS:
                    item[name]={"form":archetype,"operation":operation,
                                "strength":strength}
                rows.append(item)
    assert len(rows)==288
    digest=hashlib.sha256("\n".join(sorted(
        x["original_glb_sha256"] for x in rows)).encode()).hexdigest()
    distances={key:(.035 if key=="prior" else (.018 if good else .043))
               for key in VARIANTS}
    metrics={}
    frozen={}
    for name in VARIANTS:
        before=name=="prior"
        metrics[name]={
            "form_accuracy":.75 if before else .875,
            "mean_3d_surface_chamfer":distances[name],
            "operation_accuracy":.93,
            "strength_mae":.115,
            "predicted_distinct_archetypes":8,
            "predicted_unique_triangle_topologies":5,
            "generic_shell_output_count":0,
            "per_form":{
                form:{"count":36,"correct_form":18 if before else 36}
                for form in FORMS[1:]
            }
        }
        frozen[name]={
            "source_form_accuracy":metrics[name]["form_accuracy"],
            "predicted_unique_form_types":8
        }
    auditing={
        "schema":FORWARD,"study_id":"identity_continuation_v9",
        "source_blind_native_shapes":288,
        "real_student_generated_GLBS":1152,
        "original_validation_families":16,
        "original_validation_archetypes":8,
        "source_hashes_sha256":digest,
        "external_meshes_used":False,
        "all_source_and_reconstructed_meshes_valid":True,
        "android_deployed":False,
        "unchanged_native_surface_chamfer":.024,
        "results":metrics,
        "physical_3d_gain_vs_generic_parent":{
            name:(distances["prior"]-distances[name])/distances["prior"]
            for name in CONDITIONS
        },
        "individual_GLBS":rows
    }
    session=[{
        "condition":condition,"seed":seed,
        "actual_gradient_seconds":300.02,
        "updates":250,"selected_development_step":160,
        "old_training_retention":{"accuracy":.981}
    } for condition in CONDITIONS for seed in SEEDS]
    development={
        "replay_continuation":{"selection_priority":.80},
        "contrastive_continuation":{"selection_priority":.65},
        "spindle_truss_focus":{"selection_priority":.50}
    }
    study={
        "schema":SCHEMA,"study":"identity_continuation_v9",
        "original_v6_experimental_parent_sha256":"a"*64,
        "source_v7_hard_form_sha256":"b"*64,
        "warm_started_from_existing_neural_weights":True,
        "original_v7_teacher_old_training_form_accuracy":.98,
        "old_model_research_gate":"research_not_promoted_legacy_checkpoint_retained",
        "original_operation_and_strength_weights_frozen":True,
        "training_unique_native_form_baselines":168,
        "new_training_unique_form_baselines":64,
        "previous_training_only_unique_form_baselines":104,
        "previous_v6_blind_used_in_training":False,
        "fresh_dev_unique_native_forms":16,
        "fresh_blind_unique_native_forms":16,
        "fresh_blind_new_native_transformations":288,
        "balanced_dimensions_across_all_eight_forms":True,
        "separate_32x32_baseline_three_view_encoder":True,
        "same_start_data_budget_all_conditions":True,
        "completed_independent_sessions":6,
        "optimizer_active_seconds":1800.12,"required_seconds":1800,
        "sessions":session,
        "development":development,
        "development_only_method_selected":"spindle_truss_focus",
        "development_checkpoint_choices":{
            name:{"seed":211,"step":160} for name in CONDITIONS
        },
        "new_blind_source_sha256":digest,
        "new_blind_form_results":frozen,
        "no_pretrained_outside_AI":True,
        "android_neural_deployed":False
    }
    lineage={
        "schema":MODEL_SCHEMA,
        "parent_source_weights_sha256":"a"*64,
        "source_v7_hard_form_weights_sha256":"b"*64,
        "parent_form_class_names":list(FORMS),
        "old_operation_network_frozen":True,
        "android_approved":False,
        "identity_cameras":["side","front","top"],
        "identity_input_dim":3072,
        "identity_input_mean":[0.]*3072,
        "identity_input_std":[1.]*3072,
        "chosen_on_new_development_only":"spindle_truss_focus",
        "fresh_blind_source_sha256":digest
    }
    return study,auditing,lineage


@unittest.skipUnless(os.environ.get("ASSETWRIGHT_DINO_STUDY")=="identity_continuation_v9",
                     "Only run with original unseen v9 source families")
class ShapeKnowledgeContinuation(unittest.TestCase):
    def test_64_new_forms_and_entirely_unseen_blind(self):
        self.assertEqual(STUDY,"identity_continuation_v9")
        self.assertEqual(EXPECTED,1728)
        self.assertEqual(BASELINES,96)
        self.assertEqual({k:len(v) for k,v in FAMILIES.items()},
                         {"train":64,"development":16,"validation":16})
        self.assertEqual({k:sum(x[0]==k for x in expected_changes().values())
                          for k in FAMILIES},
                         {"train":1152,"development":288,"validation":288})
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))
        self.assertTrue(all(x.startswith("if_blind")
                            for x in FAMILIES["validation"]))
    def test_real_physical_research_review_never_auto_installs_on_android(self):
        result=assess(*fixture())
        self.assertEqual(result["status"],"eligible_for_human_research_review")
        self.assertFalse(result["android_neural_deployed"])
    def test_true_source_surface_regression_rejects_new_model(self):
        result=assess(*fixture(False))
        self.assertEqual(result["status"],"research_candidate_not_promoted")
        self.assertFalse(result["checks"]["source_aware_3d_surface_gain_vs_prior_at_least_12pct"])
    def test_source_hashes_cannot_be_reused_or_mismatched(self):
        a,b,c=fixture()
        b["source_hashes_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"Source blind original GLBs changed"):
            assess(a,b,c)
    def test_operation_model_is_immutable(self):
        a,b,c=fixture()
        b["individual_GLBS"][0]["contrastive_continuation"]["operation"]="LOWER_RECESS"
        with self.assertRaisesRegex(ValueError,"Frozen native operation"):
            assess(a,b,c)
    def test_dev_only_method_selection_prevents_blind_test_cherry_picking(self):
        a,b,c=fixture()
        a["development_only_method_selected"]="replay_continuation"
        with self.assertRaisesRegex(ValueError,"Blind data used"):
            assess(a,b,c)
    def test_prior_neural_weights_must_be_loaded_and_old_accuracy_retained(self):
        a,b,c=fixture()
        a["warm_started_from_existing_neural_weights"]=False
        with self.assertRaisesRegex(ValueError,"network changed"):
            assess(a,b,c)
        a,b,c=fixture()
        a["sessions"][4]["old_training_retention"]["accuracy"]=.40
        result=assess(a,b,c)
        self.assertFalse(result["checks"]["old_source_shape_identity_skill_retained"])


if __name__=="__main__":
    unittest.main()

"""Prove actual form classes, protected new blind cohorts and fail-closed gate."""
import hashlib
import importlib.util
import os
import unittest

from advanced_form_student import OPERATIONS
from dino_delta_school import STUDY,FAMILIES,LEVELS,EXPECTED,BASELINES,expected_changes
from native_multiform_student import (
    FORMS,VARIANTS,CONDITIONS,SEEDS,SCHEMA,MODEL_SCHEMA)
from native_multiform_forward_audit import SCHEMA as FORWARD
from native_multiform_acceptance import assess
from native_multiform_vertex import POINT_COUNT,FIELD_SIZE


def fake(pass_geometry=True):
    rows=[]
    for i,family in enumerate(FAMILIES["validation"]):
        form=FORMS[i+1]
        for op in OPERATIONS:
            for strength in LEVELS["validation"]:
                case=f"validation__{family}__{op.lower()}__s{round(strength*1000):03d}"
                row={
                    "case":case,"family":family,
                    "target_form":form,
                    "target_operation":op,
                    "target_strength":strength,
                    "original_glb_sha256":hashlib.sha256(case.encode()).hexdigest()
                }
                row.update({variant:{"strength":strength}
                            for variant in VARIANTS})
                rows.append(row)
    digest=hashlib.sha256("\n".join(sorted(
        x["original_glb_sha256"] for x in rows)).encode()).hexdigest()
    rmse={
        "prior":.08,"balanced_forms":.047,
        "geometry_forms":.039 if pass_geometry else .068,
        "geometry_hard_forms":.045
    }
    scores={}
    for variant in VARIANTS:
        chosen=variant!="prior"
        scores[variant]={
            "form_accuracy":.0 if not chosen else .90,
            "operation_accuracy":.73 if not chosen else .84,
            "strength_mae":.17 if not chosen else .115,
            "mean_3d_surface_chamfer":rmse[variant],
            "predicted_distinct_archetypes":0 if not chosen else 8,
            "predicted_unique_triangle_topologies":1 if not chosen else 6,
            "generic_shell_output_count":192 if not chosen else 0,
            "per_form":{
                form:{"count":24,"correct_form":0 if not chosen else 22}
                for form in FORMS[1:]
            }
        }
    old={"operation_accuracy":.98,"strength_mae":.036}
    evaluation={
        "schema":SCHEMA,"study_id":"multiform_v6",
        "previous_owned_parameters_reused":160938,
        "old_original_replay_cases":1680,
        "new_multiform_train_examples":672,
        "new_multiform_dev_examples":192,
        "fresh_never_inspected_blind_examples":192,
        "train_family_count":16,
        "validation_family_count":8,
        "test_topology_never_trained":True,
        "same_cpu_budget_and_start":True,
        "training_sessions":6,
        "outside_geometry_model_used":False,
        "android_deployed":False,
        "parent_sha256":"a"*64,
        "blind_source_sha256":digest,
        "unmodified_parent_predictions_max_abs_error":.0001,
        "required_optimizer_seconds":1800,
        "actual_optimizer_seconds":1800.1,
        "session_results":[{
            "condition":condition,"seed":seed,"actual_optimizer_seconds":300.016,
            "optimizer_updates":200,"dev_selected_step":160
        } for condition in CONDITIONS for seed in SEEDS],
        "frozen_blind_results":{
            name:{
                "form_accuracy":score["form_accuracy"],
                "operation_accuracy":score["operation_accuracy"],
                "strength_mae":score["strength_mae"],
                "distinct_predicted_archetypes":score["predicted_distinct_archetypes"]
            } for name,score in scores.items()
        },
        "development_only_method_selected":"geometry_forms",
        "development_scores":{
            "balanced_forms":{"development_priority":.7},
            "geometry_forms":{"development_priority":.5},
            "geometry_hard_forms":{"development_priority":.58},
        },
        "prior_old_training_metrics":old,
        "continued_old_training_metrics":{
            name:{"operation_accuracy":.99,"strength_mae":.032}
            for name in CONDITIONS
        }
    }
    forward={
        "schema":FORWARD,"study_id":"multiform_v6",
        "source_blind_native_shapes":192,
        "real_student_generated_GLBS":768,
        "original_validation_families":8,
        "original_validation_archetypes":8,
        "original_validation_topologies":1,
        "external_meshes_used":False,
        "android_deployed":False,
        "all_source_and_reconstructed_meshes_valid":True,
        "reconstruction_form_chosen_by":
            "actual student neural form head, never target form",
        "source_hashes_sha256":digest,
        "unchanged_native_surface_chamfer":.12,
        "results":scores,
        "physical_3d_gain_vs_generic_parent":{
            name:(rmse["prior"]-rmse[name])/rmse["prior"]
            for name in CONDITIONS},
        "individual_GLBS":rows
    }
    lineage={
        "schema":MODEL_SCHEMA,
        "source_parent_sha256":"a"*64,
        "blind_source_sha256":digest,
        "input_features":1536,"hidden_dim":96,
        "form_names":list(FORMS),
        "pixel_mean":[0]*1536,"pixel_std":[1]*1536,
        "development_selected_method":"geometry_forms",
        "android_deployable":False,
        "human_review_required":True,
        "operations":list(OPERATIONS)
    }
    return evaluation,forward,lineage


@unittest.skipUnless(os.getenv("ASSETWRIGHT_DINO_STUDY")=="multiform_v6",
                     "New multi-form study must be selected explicitly")
class DiverseGeometryLearningTests(unittest.TestCase):
    def test_eight_entirely_new_form_schools_and_blind_topology(self):
        self.assertEqual(STUDY,"multiform_v6")
        self.assertEqual(len(FORMS),9)
        self.assertEqual(EXPECTED,1056)
        self.assertEqual(BASELINES,32)
        self.assertEqual(len(expected_changes()),1056)
        self.assertEqual(POINT_COUNT,64)
        self.assertEqual(FIELD_SIZE,192)
        expected={"train":672,"development":192,"validation":192}
        for phase,num in expected.items():
            self.assertEqual(sum(x[0]==phase
                for x in expected_changes().values()),num)
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))
        self.assertTrue(all(f.startswith("mf_blind")
                            for f in FAMILIES["validation"]))

    def test_only_real_multi_form_blind_3d_gain_allows_research_review(self):
        report=assess(*fake())
        self.assertEqual(report["status"],"eligible_for_human_research_review")
        self.assertFalse(report["android_deployed"])
        self.assertEqual(report["predicted_different_forms"],8)

    def test_renamed_generic_shape_cannot_pass(self):
        a,b,c=fake()
        b["results"]["geometry_forms"]["predicted_distinct_archetypes"]=1
        a["frozen_blind_results"]["geometry_forms"]["distinct_predicted_archetypes"]=1
        report=assess(a,b,c)
        self.assertFalse(report["checks"]["at_least_eight_distinct_3d_forms_predicted"])
        self.assertEqual(report["status"],
                         "research_not_promoted_legacy_checkpoint_retained")

    def test_no_improvement_on_true_3d_surfaces_is_not_called_learning(self):
        report=assess(*fake(False))
        self.assertFalse(report["checks"][
            "multi_form_geometry_loss_beats_replay_control"])

    def test_blind_score_cannot_choose_different_training_method(self):
        a,b,c=fake()
        a["development_only_method_selected"]="geometry_hard_forms"
        with self.assertRaisesRegex(ValueError,"After-the-fact"):
            assess(a,b,c)

    def test_new_source_GLBS_must_match_visual_forward_models(self):
        a,b,c=fake()
        b["source_hashes_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"not identical"):
            assess(a,b,c)
        a,b,c=fake()
        b["results"]["geometry_forms"]["form_accuracy"]+=.12
        with self.assertRaisesRegex(ValueError,"Unaligned"):
            assess(a,b,c)

    def test_incomplete_training_or_pretrained_3d_is_rejected(self):
        a,b,c=fake()
        a["actual_optimizer_seconds"]=50
        with self.assertRaisesRegex(ValueError,"30 minutes"):
            assess(a,b,c)
        a,b,c=fake()
        b["external_meshes_used"]=True
        with self.assertRaisesRegex(ValueError,"Forbidden"):
            assess(a,b,c)

    @unittest.skipUnless(importlib.util.find_spec("torch") is not None,
                         "Optional CPU Torch only required in actual neural job")
    def test_native_vertex_supervision_updates_form_and_geometry_heads(self):
        import torch
        from native_multiform_vertex import proxy_loss
        ops=torch.randn(4,6,requires_grad=True)
        powers=torch.rand(4,6,requires_grad=True)
        classes=torch.randn(4,9,requires_grad=True)
        target_ops=torch.tensor([1,2,4,5])
        target_forms=torch.tensor([2,3,5,8])
        basis=torch.randn(4,6,FIELD_SIZE)*.2
        actual=.45*basis[torch.arange(4),target_ops]
        loss=proxy_loss(ops,powers,classes,
                        target_ops,target_forms,basis,actual)
        loss.backward()
        self.assertGreater(float(classes.grad.abs().sum()),0)
        self.assertGreater(float(ops.grad.abs().sum()),0)
        self.assertGreater(float(powers.grad.abs().sum()),0)


if __name__=="__main__":
    unittest.main()

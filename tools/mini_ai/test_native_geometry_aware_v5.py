"""Offline regression tests for honest geometry-supervised cumulative learning."""
from __future__ import annotations
import hashlib
import importlib.util
import os
import unittest

from advanced_form_student import OPERATIONS
from dino_delta_school import STUDY,FAMILIES,LEVELS,EXPECTED,BASELINES,expected_changes
from native_geometry_aware_student import SCHEMA,MODEL_SCHEMA,CONDITIONS,VARIANTS,SEEDS
from native_geometry_aware_forward_audit import SCHEMA as FORWARD
from native_geometry_aware_acceptance import reconcile
from native_vertex_supervision import VERTEX_IDS,SAMPLE_SIZE


def fixture(good=True):
    cases=[]
    for family in FAMILIES["validation"]:
        for op in OPERATIONS:
            for level in LEVELS["validation"]:
                name=f"validation__{family}__{op.lower()}__s{round(level*1000):03d}"
                row={
                    "case":name,"family":family,
                    "target_operation":op,"target_strength":level,
                    "reference_glb_sha256":hashlib.sha256(name.encode()).hexdigest()
                }
                row.update({variant:{"strength":level} for variant in VARIANTS})
                cases.append(row)
    sha=hashlib.sha256("\n".join(sorted(
        r["reference_glb_sha256"] for r in cases)).encode()).hexdigest()
    measures={
        "prior":(.79,.16,.0060),
        "replay_only":(.81,.15,.0058),
        "geometry_supervised":(.84,.14,.0055 if good else .0062),
        "geometry_hard_mining":(.83,.147,.00565)
    }
    real={
        key:{
            "operation_accuracy":accuracy,
            "strength_mae":strength,
            "mean_normalized_vertex_rmse":rmse,
            "per_operation":{op:{"count":16} for op in OPERATIONS}
        } for key,(accuracy,strength,rmse) in measures.items()
    }
    original=real["prior"]["mean_normalized_vertex_rmse"]
    nochange=.015
    forward={
        "schema":FORWARD,"study_id":"geometry_aware_v5",
        "actual_original_Kotlin_blind_GLBS":96,
        "real_original_Kotlin_reconstructed_GLBS":384,
        "source_family_count":4,
        "source_hashes_sha256":sha,
        "external_AI_meshes_used":False,
        "source_topology_checked":True,
        "android_deployed":False,
        "unchanged_reference_RMSE":nochange,
        "variants":real,
        "geometry_gains":{
            key:{"vs_prior":(original-val["mean_normalized_vertex_rmse"])/original,
                 "vs_unchanged":(nochange-val["mean_normalized_vertex_rmse"])/nochange}
            for key,val in real.items() if key!="prior"
        },
        "individual_original_GLBS":cases
    }
    sessions=[{
        "condition":mode,"seed":seed,
        "actual_optimizer_seconds":300.25,
        "gradient_updates":2000,
        "selected_fresh_development_step":500
    } for mode in CONDITIONS for seed in SEEDS]
    evaluation={
        "schema":SCHEMA,"study":"geometry_aware_v5",
        "retained_old_network_was_reloaded":True,
        "normalization_rebase_max_prediction_error":.00002,
        "earlier_v3_source_examples":672,
        "earlier_v4_failed_candidate_correct_source_examples":504,
        "real_Kotlin_prior_training_GLBS_replayed":1176,
        "new_v5_training_examples":504,
        "new_v5_development_examples":96,
        "new_v5_blind_examples":96,
        "sampled_native_vertices_per_training_target":64,
        "same_original_start_all_conditions":True,
        "same_training_data_and_cpu_budget":True,
        "heldout_not_in_any_model_selection":True,
        "completed_independent_sessions":6,
        "starting_learned_checkpoint_sha256":"f"*64,
        "outside_pretrained_model_used":False,
        "outside_mesh_generation_used":False,
        "android_deployed":False,
        "required_optimizer_seconds":1800,
        "actual_training_optimizer_seconds":1801.5,
        "session_provenance":sessions,
        "fresh_blind_results":{
            key:{"operation_accuracy":measure["operation_accuracy"],
                 "strength_mae":measure["strength_mae"]}
            for key,measure in real.items()},
        "fresh_development_model_comparison":{
            key:{"selection_priority":p} for key,p in
            [("prior",.99),("replay_only",.92),("geometry_supervised",.80),
             ("geometry_hard_mining",.84)]
        },
        "chosen_method_from_development_only":"geometry_supervised",
        "retained_old_training_before":{
            "operation_accuracy":.982,"strength_mae":.046},
        "retained_old_training_after":{
            key:{"operation_accuracy":.978,"strength_mae":.047} for key in CONDITIONS
        },
        "blind_original_GLBS_digest":sha,
    }
    lineage={
        "schema":MODEL_SCHEMA,
        "parent_sha256":"f"*64,
        "child_selected_by_development_only":"geometry_supervised",
        "validation_family_untouched_until_frozen":True,
        "input_dim":1536,"hidden_dim":96,
        "operation_names":list(OPERATIONS),
        "input_mean":[0.]*1536,"input_std":[1.]*1536,
        "approved_for_android":False,
        "human_visual_review_required":True,
        "blind_source_sha256":sha
    }
    return evaluation,forward,lineage


@unittest.skipUnless(os.getenv("ASSETWRIGHT_DINO_STUDY")=="geometry_aware_v5",
                     "Run only against truly fresh v5 family curriculum")
class RealOriginalGeometryCurriculumTests(unittest.TestCase):
    def test_all_new_training_sources_are_completely_disjoint(self):
        self.assertEqual(STUDY,"geometry_aware_v5")
        self.assertEqual(EXPECTED,696)
        self.assertEqual(BASELINES,20)
        self.assertEqual(len(expected_changes()),696)
        for split,n in (("train",504),("development",96),("validation",96)):
            self.assertEqual(sum(x[0]==split for x in expected_changes().values()),n)
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))
        self.assertTrue(all(x.startswith("bg_blind")
                            for x in FAMILIES["validation"]))
        self.assertEqual(len(VERTEX_IDS),64)
        self.assertEqual(SAMPLE_SIZE,192)
        self.assertEqual(len(set(VERTEX_IDS)),len(VERTEX_IDS))

    def test_genuine_3D_gain_only_allows_human_research_review(self):
        result=reconcile(*fixture())
        self.assertEqual(result["disposition"],"eligible_for_human_research_review")
        self.assertFalse(result["android_deployed"])
        self.assertTrue(result["human_review_required_for_mobile"])

    def test_real_glb_regression_prevents_knowledge_promotion(self):
        result=reconcile(*fixture(good=False))
        self.assertEqual(result["disposition"],
                         "prior_checkpoint_retained_new_candidate_rejected")
        self.assertFalse(result["checks"][
            "physical_3D_mesh_better_than_stored_prior_by_2pct"])

    def test_no_training_or_replay_or_old_checkpoint_is_rejected(self):
        a,b,c=fixture()
        a["real_Kotlin_prior_training_GLBS_replayed"]=0
        with self.assertRaisesRegex(ValueError,"incomplete"):
            reconcile(a,b,c)
        a,b,c=fixture()
        a["retained_old_network_was_reloaded"]=False
        with self.assertRaisesRegex(ValueError,"incomplete"):
            reconcile(a,b,c)
        a,b,c=fixture()
        a["actual_training_optimizer_seconds"]=200
        with self.assertRaisesRegex(ValueError,"optimizer"):
            reconcile(a,b,c)

    def test_development_selection_cannot_be_replaced_using_blind_results(self):
        a,b,c=fixture()
        a["chosen_method_from_development_only"]="geometry_hard_mining"
        with self.assertRaisesRegex(ValueError,"development-selected"):
            reconcile(a,b,c)

    def test_source_hash_and_forwards_must_match(self):
        a,b,c=fixture()
        b["source_hashes_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"SHA mismatch"):
            reconcile(a,b,c)
        a,b,c=fixture()
        b["variants"]["geometry_supervised"]["strength_mae"]+=.05
        with self.assertRaisesRegex(ValueError,"disagree"):
            reconcile(a,b,c)

    def test_teacher_and_android_do_not_enter_learning(self):
        a,b,c=fixture()
        a["outside_pretrained_model_used"]=True
        with self.assertRaisesRegex(ValueError,"Forbidden"):
            reconcile(a,b,c)
        a,b,c=fixture()
        c["approved_for_android"]=True
        with self.assertRaisesRegex(ValueError,"Forbidden"):
            reconcile(a,b,c)

    @unittest.skipUnless(importlib.util.find_spec("torch") is not None,
                         "Optional training-only CPU torch not installed")
    def test_true_vertex_proxy_loss_trains_strength_AND_operation_heads(self):
        import torch
        from native_vertex_supervision import proxy_loss,difficulty_scores
        scores=torch.tensor([[.10,.2,.3,.4,.5,.6],[.2,.5,.4,.3,.2,.1]],
                            requires_grad=True)
        strength=torch.tensor([[.30]*6,[.70]*6],requires_grad=True)
        basis=torch.randn(2,6,SAMPLE_SIZE)*.04
        ops=torch.tensor([1,3])
        targets=.65*basis[torch.arange(2),ops]
        error=proxy_loss(scores,strength,basis,targets,ops)
        error.backward()
        self.assertTrue(torch.isfinite(scores.grad).all())
        self.assertTrue(torch.isfinite(strength.grad).all())
        self.assertGreater(float(scores.grad.abs().sum()),0)
        self.assertGreater(float(strength.grad.abs().sum()),0)
        hard=difficulty_scores(scores.detach(),strength.detach(),
                               ops,torch.tensor([.2,.9]))
        self.assertEqual(tuple(hard.shape),(2,))
        self.assertFalse(hard.requires_grad)


if __name__=="__main__":
    unittest.main()

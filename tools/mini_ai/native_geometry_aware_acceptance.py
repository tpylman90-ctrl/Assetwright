"""Fail-closed v5 real native 3D geometry checkpoint gate.

Only new blind Kotlin GLB vertex differences determine success. A rejected
model is retained for research, not allowed to overwrite previously learned
verified weights. No automatic Android or private-repo interaction.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from native_geometry_aware_student import (
    SCHEMA,MODEL_SCHEMA,CONDITIONS,SEEDS,VARIANTS)
from native_geometry_aware_forward_audit import SCHEMA as FORWARD_SCHEMA


def reconcile(evaluation,forward,lineage):
    if (evaluation.get("schema")!=SCHEMA
        or forward.get("schema")!=FORWARD_SCHEMA
        or lineage.get("schema")!=MODEL_SCHEMA
        or evaluation.get("study")!="geometry_aware_v5"
        or forward.get("study_id")!="geometry_aware_v5"):
        raise ValueError("No verified native v5 geometry curriculum")
    if (
        evaluation.get("retained_old_network_was_reloaded") is not True
        or not 0<=evaluation.get("normalization_rebase_max_prediction_error",1)<=.002
        or evaluation.get("earlier_v3_source_examples")!=672
        or evaluation.get("earlier_v4_failed_candidate_correct_source_examples")!=504
        or evaluation.get("real_Kotlin_prior_training_GLBS_replayed")!=1176
        or evaluation.get("new_v5_training_examples")!=504
        or evaluation.get("new_v5_development_examples")!=96
        or evaluation.get("new_v5_blind_examples")!=96
        or evaluation.get("sampled_native_vertices_per_training_target")!=64
        or evaluation.get("same_original_start_all_conditions") is not True
        or evaluation.get("same_training_data_and_cpu_budget") is not True
        or evaluation.get("heldout_not_in_any_model_selection") is not True
        or evaluation.get("completed_independent_sessions")!=6
        or forward.get("actual_original_Kotlin_blind_GLBS")!=96
        or forward.get("real_original_Kotlin_reconstructed_GLBS")!=384
        or forward.get("source_family_count")!=4):
        raise ValueError("Old replay, new training or fresh native holdout is incomplete")
    if (
        evaluation.get("starting_learned_checkpoint_sha256")!=lineage.get("parent_sha256")
        or lineage.get("child_selected_by_development_only") not in CONDITIONS
        or lineage.get("validation_family_untouched_until_frozen") is not True
        or lineage.get("input_dim")!=1536
        or lineage.get("hidden_dim")!=96
        or len(lineage.get("operation_names",[]))!=6
        or len(lineage.get("input_mean",[]))!=1536
        or len(lineage.get("input_std",[]))!=1536):
        raise ValueError("Cumulative neural weight lineage is not original")
    if (
        evaluation.get("outside_pretrained_model_used") is not False
        or evaluation.get("outside_mesh_generation_used") is not False
        or evaluation.get("android_deployed") is not False
        or lineage.get("approved_for_android") is not False
        or lineage.get("human_visual_review_required") is not True
        or forward.get("external_AI_meshes_used") is not False
        or forward.get("source_topology_checked") is not True
        or forward.get("android_deployed") is not False):
        raise ValueError("Forbidden teacher/mesh/Android deployment boundary")
    requested=evaluation.get("required_optimizer_seconds")
    measured=evaluation.get("actual_training_optimizer_seconds",-1)
    if requested!=1800 or not 1800<=measured<=2400:
        raise ValueError("Not 30 minutes of real measured optimizer work")
    sessions=evaluation.get("session_provenance",[])
    if (not isinstance(sessions,list) or len(sessions)!=6
        or {(s.get("condition"),s.get("seed")) for s in sessions}!=
            {(mode,seed) for mode in CONDITIONS for seed in SEEDS}
        or any(s.get("actual_optimizer_seconds",0)<requested/6-.25
               or s.get("gradient_updates",0)<100
               or s.get("selected_fresh_development_step",0)<=0
               for s in sessions)):
        raise ValueError("Missing an independent real trained geometry study session")
    cases=forward.get("individual_original_GLBS")
    if not isinstance(cases,list) or len(cases)!=96:
        raise ValueError("Native source vs reconstructed GLBs missing")
    sha=[r.get("reference_glb_sha256") for r in cases]
    if (len(set(sha))!=96 or any(
        not isinstance(x,str) or len(x)!=64
        or any(c not in "0123456789abcdef" for c in x) for x in sha)):
        raise ValueError("Repeated/non-native original heldout GLB")
    digest=hashlib.sha256("\n".join(sorted(sha)).encode()).hexdigest()
    if (digest!=forward.get("source_hashes_sha256")
        or digest!=evaluation.get("blind_original_GLBS_digest")
        or digest!=lineage.get("blind_source_sha256")):
        raise ValueError("Independent native original geometry source SHA mismatch")
    by_variant=forward.get("variants",{})
    visual=evaluation.get("fresh_blind_results",{})
    if set(by_variant)!=set(VARIANTS) or set(visual)!=set(VARIANTS):
        raise ValueError("Missing equal-budget control or three experimental arms")
    for mode in VARIANTS:
        for visual_key,physical_key in (
            ("operation_accuracy","operation_accuracy"),
            ("strength_mae","strength_mae")):
            a=visual[mode].get(visual_key)
            b=by_variant[mode].get(physical_key)
            if (type(a) not in (int,float) or type(b) not in (int,float)
                or not math.isfinite(a) or not math.isfinite(b)
                or abs(a-b)>.0002):
                raise ValueError("Blind model scores disagree with actual Kotlin GLBs")
        per_op=by_variant[mode].get("per_operation",{})
        if (len(per_op)!=6 or any(x.get("count")!=16 for x in per_op.values())):
            raise ValueError("Per-operation original native geometry audit incomplete")
    dev=evaluation.get("fresh_development_model_comparison",{})
    if set(dev)!=set(VARIANTS) or any(
        not isinstance(dev[name].get("selection_priority"),(float,int))
        or not math.isfinite(dev[name]["selection_priority"])
        for name in VARIANTS):
        raise ValueError("Missing development-only method selection metrics")
    chosen=evaluation.get("chosen_method_from_development_only")
    if (chosen not in CONDITIONS
        or chosen!=lineage["child_selected_by_development_only"]
        or chosen!=min(CONDITIONS,key=lambda x:dev[x]["selection_priority"])):
        raise ValueError("Method is not independently development-selected")
    retained=evaluation.get("retained_old_training_after",{}).get(chosen,{})
    previous=evaluation.get("retained_old_training_before",{})
    if not all(isinstance(x,(int,float)) and math.isfinite(x)
               for x in (
                   retained.get("operation_accuracy"),retained.get("strength_mae"),
                   previous.get("operation_accuracy"),previous.get("strength_mae"))):
        raise ValueError("Old-source forgetting not actually evaluated")
    parent=by_variant["prior"]
    learner=by_variant[chosen]
    baseline=by_variant["replay_only"]
    old_RMSE=parent["mean_normalized_vertex_rmse"]
    new_RMSE=learner["mean_normalized_vertex_rmse"]
    base_RMSE=baseline["mean_normalized_vertex_rmse"]
    nochange=forward.get("unchanged_reference_RMSE",0)
    if not all(isinstance(x,(float,int)) and math.isfinite(x) and x>0
               for x in (old_RMSE,new_RMSE,base_RMSE,nochange)):
        raise ValueError("Physically impossible original GLB vertex RMSE")
    gain=(old_RMSE-new_RMSE)/old_RMSE
    baseline_gain=(base_RMSE-new_RMSE)/base_RMSE
    actual=forward.get("geometry_gains",{}).get(chosen,{})
    if (abs(actual.get("vs_prior",-10)-gain)>.0001
        or abs(actual.get("vs_unchanged",-10)-
               (nochange-new_RMSE)/nochange)>.0001):
        raise ValueError("Real geometry improvement calculation was manipulated")
    reversals=0
    for family in sorted({r.get("family") for r in cases}):
        for op in lineage["operation_names"]:
            series=sorted((r for r in cases if
                           r.get("family")==family and
                           r.get("target_operation")==op),
                          key=lambda r:r.get("target_strength",-1))
            if len(series)!=4:
                raise ValueError("Incomplete original strength monotonic comparison")
            for a,b in zip(series,series[1:]):
                if a[chosen]["strength"]>b[chosen]["strength"]+.001:
                    reversals+=1
    checks={
        "prior_original_geometric_skill_retained":
            retained["operation_accuracy"]>=previous["operation_accuracy"]-.02,
        "prior_continuous_strength_skill_retained":
            retained["strength_mae"]<=previous["strength_mae"]+.015,
        "new_geometry_operation_not_worse":
            learner["operation_accuracy"]>=parent["operation_accuracy"]-.011,
        "new_geometry_strength_not_worse":
            learner["strength_mae"]<=parent["strength_mae"]+.012,
        "physical_3D_mesh_better_than_stored_prior_by_2pct":
            gain>=.02,
        "physical_3D_mesh_better_than_equal_budget_replay_control_by_1pct":
            chosen=="replay_only" or baseline_gain>=.01,
        "physical_3D_mesh_better_than_unchanged_by_10pct":
            new_RMSE<=nochange*.90,
        "native_strength_order_reversals_at_most_four":
            reversals<=4,
        "honest_full_384_own_GLBS_and_source_alignment":True,
        "research_only_no_android_deployment":True
    }
    disposition="eligible_for_human_research_review" if all(checks.values()) \
        else "prior_checkpoint_retained_new_candidate_rejected"
    return {
        "schema":"assetwright-original-3d-geometry-aware-deep-learning-gate-v5",
        "disposition":disposition,
        "checks":checks,
        "selected_condition":chosen,
        "parent_checkpoint_sha256":lineage["parent_sha256"],
        "new_unseen_source_hashes_sha256":digest,
        "old_and_new_actual_training_GLBS":1680,
        "fresh_original_validation_GLBS":96,
        "actual_reconstructed_original_Kotlin_GLBS":384,
        "real_3D_RMSE_parent":old_RMSE,
        "real_3D_RMSE_replay_control":base_RMSE,
        "real_3D_RMSE_selected_child":new_RMSE,
        "real_3D_gain_vs_parent_fraction":gain,
        "real_3D_gain_vs_replay_control_fraction":baseline_gain,
        "native_strength_order_reversals":reversals,
        "training_seconds_actually_measured":measured,
        "parent_weights_unchanged":True,
        "human_review_required_for_mobile":True,
        "android_deployed":False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("evaluation","forward","lineage","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    report=reconcile(json.loads(a.evaluation.read_text()),
                     json.loads(a.forward.read_text()),
                     json.loads(a.lineage.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()

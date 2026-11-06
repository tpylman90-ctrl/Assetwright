"""Fail-closed source-hashed v6 skill-preserving 8-form geometry gate.

Rejects mode collapse, generic-shell fallback, topology-only renames,
poor reconstruction and older-learning regressions. Never selects
a different mode after seeing blind cases. Passing research gate still
requires human review before installing a mobile learned model.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from native_multiform_student import (
    CONDITIONS,FORMS,VARIANTS,SEEDS,SCHEMA,MODEL_SCHEMA)
from native_multiform_forward_audit import SCHEMA as FORWARD


def assess(evaluation,geometry,lineage):
    if (evaluation.get("schema")!=SCHEMA or
        geometry.get("schema")!=FORWARD or
        lineage.get("schema")!=MODEL_SCHEMA or
        geometry.get("study_id")!="multiform_v6" or
        evaluation.get("study_id")!="multiform_v6"):
        raise ValueError("No genuine original multi-form model study identity")
    if (
        evaluation.get("previous_owned_parameters_reused")!=160938 or
        evaluation.get("old_original_replay_cases")!=1680 or
        evaluation.get("new_multiform_train_examples")!=672 or
        evaluation.get("new_multiform_dev_examples")!=192 or
        evaluation.get("fresh_never_inspected_blind_examples")!=192 or
        evaluation.get("train_family_count")!=16 or
        evaluation.get("validation_family_count")!=8 or
        evaluation.get("test_topology_never_trained") is not True or
        evaluation.get("same_cpu_budget_and_start") is not True or
        evaluation.get("training_sessions")!=6 or
        geometry.get("source_blind_native_shapes")!=192 or
        geometry.get("real_student_generated_GLBS")!=768 or
        geometry.get("original_validation_families")!=8 or
        geometry.get("original_validation_archetypes")!=8 or
        geometry.get("original_validation_topologies")!=1):
        raise ValueError("No full multiple-form/tessellation-independent evidence")
    if (
        evaluation.get("outside_geometry_model_used") is not False or
        evaluation.get("android_deployed") is not False or
        geometry.get("external_meshes_used") is not False or
        geometry.get("all_source_and_reconstructed_meshes_valid") is not True or
        geometry.get("reconstruction_form_chosen_by")!=
            "actual student neural form head, never target form" or
        geometry.get("android_deployed") is not False or
        lineage.get("android_deployable") is not False or
        lineage.get("human_review_required") is not True):
        raise ValueError("Forbidden externally generated mesh or Android training data")
    if (
        evaluation.get("parent_sha256")!=lineage.get("source_parent_sha256")
        or evaluation.get("blind_source_sha256")!=lineage.get("blind_source_sha256")
        or lineage.get("input_features")!=1536 or
        lineage.get("hidden_dim")!=96 or
        tuple(lineage.get("form_names",[]))!=FORMS or
        len(lineage.get("pixel_mean",[]))!=1536 or
        len(lineage.get("pixel_std",[]))!=1536 or
        evaluation.get("unmodified_parent_predictions_max_abs_error",1)>.002):
        raise ValueError("Original previous model weights or input feature rebase changed")
    duration=evaluation.get("actual_optimizer_seconds",0)
    if (evaluation.get("required_optimizer_seconds")!=1800
        or not isinstance(duration,(int,float))
        or not 1800<=duration<=2400):
        raise ValueError("30 minutes of actual cumulative model training not measured")
    history=evaluation.get("session_results")
    if (not isinstance(history,list) or len(history)!=6 or
        {(r.get("condition"),r.get("seed")) for r in history}!=
          {(name,seed) for name in CONDITIONS for seed in SEEDS}
        or any(r.get("actual_optimizer_seconds",0)<299
               or r.get("optimizer_updates",0)<=100
               or r.get("dev_selected_step",0)<=0 for r in history)):
        raise ValueError("Six independent trained real-shape sessions absent")
    rows=geometry.get("individual_GLBS")
    if not isinstance(rows,list) or len(rows)!=192:
        raise ValueError("Missing native 3D blind surface/geometry records")
    digests=[r.get("original_glb_sha256") for r in rows]
    if len(set(digests))!=192 or any(
        not isinstance(x,str) or len(x)!=64 or
        any(c not in "0123456789abcdef" for c in x)
        for x in digests):
        raise ValueError("Repeated or changed native original 3D source GLBs")
    sha=hashlib.sha256("\n".join(sorted(digests)).encode()).hexdigest()
    if (sha!=geometry.get("source_hashes_sha256")
        or sha!=evaluation.get("blind_source_sha256")
        or sha!=lineage.get("blind_source_sha256")):
        raise ValueError("Blind source GLBs not identical across training/audit")
    candidates=evaluation.get("frozen_blind_results",{})
    measured=geometry.get("results",{})
    development=evaluation.get("development_scores",{})
    if (set(candidates)!=set(VARIANTS) or set(measured)!=set(VARIANTS) or
        set(development)!=set(CONDITIONS)):
        raise ValueError("Missing comparator baseline or complete multi-form model")
    for variant in VARIANTS:
        for visual_key,physical_key in (
            ("form_accuracy","form_accuracy"),
            ("operation_accuracy","operation_accuracy"),
            ("strength_mae","strength_mae"),
            ("distinct_predicted_archetypes","predicted_distinct_archetypes")):
            a=candidates[variant].get(visual_key)
            b=measured[variant].get(physical_key)
            if (not isinstance(a,(int,float)) or
                not isinstance(b,(int,float)) or
                not math.isfinite(a) or not math.isfinite(b) or
                abs(a-b)>.0002):
                raise ValueError("Unaligned original image predictions and real mesh results")
        forms=measured[variant].get("per_form",{})
        if set(forms)!=set(FORMS[1:]) or any(
            c.get("count")!=24 for c in forms.values()):
            raise ValueError("A missing 3D archetype was disguised by overall accuracy")
    chosen=evaluation.get("development_only_method_selected")
    if (chosen not in CONDITIONS or
        chosen!=lineage.get("development_selected_method") or
        chosen!=min(CONDITIONS,
            key=lambda k:development[k]["development_priority"])):
        raise ValueError("After-the-fact model selection on blind shapes forbidden")
    former=evaluation.get("prior_old_training_metrics",{})
    recalled=evaluation.get("continued_old_training_metrics",{}).get(chosen,{})
    if any(
        key not in former or key not in recalled or
        not all(isinstance(m.get(key),(int,float)) and math.isfinite(m[key])
                for m in (former,recalled))
        for key in ("operation_accuracy","strength_mae")):
        raise ValueError("Older previously trained knowledge retention unverified")
    source=measured["prior"]
    learner=measured[chosen]
    replay=measured["balanced_forms"]
    base=geometry.get("unchanged_native_surface_chamfer",0)
    old_distance=source["mean_3d_surface_chamfer"]
    actual_distance=learner["mean_3d_surface_chamfer"]
    if any(not isinstance(value,(float,int)) or not math.isfinite(value)
           or value<=0 for value in
           (base,old_distance,actual_distance,replay["mean_3d_surface_chamfer"])):
        raise ValueError("Invalid real native cross-topology geometric distance")
    gain=(old_distance-actual_distance)/old_distance
    baseline_gain=(replay["mean_3d_surface_chamfer"]-
                   actual_distance)/replay["mean_3d_surface_chamfer"]
    stated=geometry["physical_3d_gain_vs_generic_parent"][chosen]
    if abs(stated-gain)>.0001:
        raise ValueError("Actual original 3D Chamfer improvement tampered")
    # Check controls increasing strength for SAME original object+op.
    inversions=0
    for family in sorted({item["family"] for item in rows}):
        for op in lineage["operations"]:
            series=sorted((r for r in rows
                if r["family"]==family and r["target_operation"]==op),
                key=lambda x:x["target_strength"])
            if len(series)!=4:
                raise ValueError("Missing original per-form original strength sequence")
            inversions+=sum(
                a[chosen]["strength"]>b[chosen]["strength"]+.001
                for a,b in zip(series,series[1:]))
    min_recall=sum(
        form["correct_form"]>=12 for form in learner["per_form"].values())
    checks={
        "old_operation_accuracy_retained":
            recalled["operation_accuracy"]>=former["operation_accuracy"]-.025,
        "old_strength_accuracy_retained":
            recalled["strength_mae"]<=former["strength_mae"]+.02,
        "archetype_classification_at_least_75pct":
            learner["form_accuracy"]>=.75,
        "all_eight_form_types_have_nontrivial_recall":
            min_recall==8,
        "no_generic_tube_collapse":
            learner["generic_shell_output_count"]<=12,
        "at_least_eight_distinct_3d_forms_predicted":
            learner["predicted_distinct_archetypes"]==8,
        "at_least_four_distinct_actual_mesh_topologies":
            learner["predicted_unique_triangle_topologies"]>=4,
        "learned_operation_accuracy_at_least_70pct":
            learner["operation_accuracy"]>=.70,
        "learned_strength_mae_at_most_point20":
            learner["strength_mae"]<=.20,
        "physical_3d_surface_better_than_generic_parent_by_12pct":
            gain>=.12,
        "physical_3d_better_than_no_change_by_10pct":
            actual_distance<=base*.90,
        "multi_form_geometry_loss_beats_replay_control":
            chosen=="balanced_forms" or baseline_gain>=.02,
        "monotonic_strength_inversions_at_most_12":inversions<=12,
        "independent_192_source_hashes_and_768_real_glbs":True,
        "no_android_auto_deployment":True
    }
    status="eligible_for_human_research_review" if all(checks.values()) \
        else "research_not_promoted_legacy_checkpoint_retained"
    return {
        "schema":"assetwright-form-diversity-real-3d-acceptance-v6",
        "status":status,
        "checks":checks,
        "method_selected_on_development_only":chosen,
        "retained_original_model_sha256":lineage["source_parent_sha256"],
        "fresh_blind_original_mesh_hashes_sha256":sha,
        "actual_CPU_training_seconds":duration,
        "old_neural_lessons_replayed":1680,
        "new_8_form_train_cases":672,
        "new_blind_original_forms":192,
        "real_original_student_GLBS":768,
        "predicted_different_forms":learner["predicted_distinct_archetypes"],
        "predicted_distinct_mesh_topologies":learner["predicted_unique_triangle_topologies"],
        "form_accuracy":learner["form_accuracy"],
        "operation_accuracy":learner["operation_accuracy"],
        "strength_mae":learner["strength_mae"],
        "physical_surface_error_parent":old_distance,
        "physical_surface_error_replay_only":replay["mean_3d_surface_chamfer"],
        "physical_surface_error_child":actual_distance,
        "physical_improvement_vs_parent":gain,
        "physical_improvement_vs_equal_budget_replay":baseline_gain,
        "ordered_strength_reversals":inversions,
        "parent_model_preserved":True,
        "human_visual_review_required":True,
        "android_deployed":False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("evaluation","forward","lineage","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    result=assess(json.loads(a.evaluation.read_text()),
                  json.loads(a.forward.read_text()),
                  json.loads(a.lineage.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()

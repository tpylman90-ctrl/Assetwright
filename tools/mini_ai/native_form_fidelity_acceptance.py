"""No-posthoc-selection v8 research gate: ORIGINAL 3D geometry fidelity.

A passing training workflow does not imply an improved neural model.
Only the DEVELOPMENT-selected adapter is eligible, and only if new
independently generated Kotlin GLBs improve physical 3D geometry while
retaining legacy modeling skills and multi-form output diversity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from native_form_fidelity_v8 import (
    SCHEMA,WEIGHT_SCHEMA,STUDY_NAME,CONDITIONS,VARIANTS,SEEDS)
from native_form_fidelity_forward_audit import SCHEMA as FORWARD


def assess(report,geometry,lineage):
    if (report.get("schema")!=SCHEMA
        or geometry.get("schema")!=FORWARD
        or lineage.get("schema")!=WEIGHT_SCHEMA
        or report.get("study")!=STUDY_NAME
        or geometry.get("study_id")!=STUDY_NAME):
        raise ValueError("Source-hashed v8 study/model identity mismatch")
    if not (
        report.get("both_existing_neural_networks_frozen") is True
        and lineage.get("legacy_action_weights_frozen") is True
        and lineage.get("legacy_shape_identity_weights_frozen") is True
        and report.get("old_v6_experimental_parent_sha256")==
            lineage.get("source_v6_weight_sha256")
        and report.get("old_v7_experimental_identity_sha256")==
            lineage.get("source_v7_form_weight_sha256")
        and report.get("older_correct_original_train_sources")==1200
        and report.get("new_original_shape_train_examples")==1152
        and report.get("new_development_examples")==288
        and report.get("new_fresh_unseen_blind_examples")==288
        and report.get("new_shape_train_families")==48
        and report.get("fresh_blind_form_families")==16
        and report.get("three_methods_equal_start_and_cpu_time") is True):
        raise ValueError("Source replay, frozen older knowledge or independent training incomplete")
    if (
        report.get("geometry_supervision_only_original_kotlin_GLBS") is not True
        or report.get("external_teacher_used") is not False
        or report.get("android_neural_deployed") is not False
        or lineage.get("not_approved_for_android") is not True
        or geometry.get("external_meshes_used") is not False
        or geometry.get("android_deployed") is not False
        or geometry.get("all_source_and_reconstructed_meshes_valid") is not True
        or geometry.get("reconstruction_form_chosen_by")!=
            "actual student neural form head, never target form"):
        raise ValueError("Outside mesh, leaked source class or Android deployment forbidden")
    duration=report.get("measured_optimizer_seconds",0)
    if (report.get("configured_optimizer_seconds")!=1800
        or not isinstance(duration,(float,int))
        or not 1800<=duration<=2400
        or report.get("completed_sessions")!=6):
        raise ValueError("Six real CPU gradient sessions must run for 1800 seconds")
    sessions=report.get("sessions")
    if (not isinstance(sessions,list) or len(sessions)!=6
        or {(x.get("condition"),x.get("seed")) for x in sessions}!=
            {(c,s) for c in CONDITIONS for s in SEEDS}
        or any(x.get("actual_optimizer_seconds",0)<299
               or x.get("optimizer_updates",0)<100
               or x.get("selected_development_step",0)<100
               for x in sessions)):
        raise ValueError("Original six-session experimental learning evidence missing")
    development=report.get("development_results",{})
    selected=report.get("development_selected")
    if (set(development)!=set(CONDITIONS)
        or selected not in CONDITIONS
        or selected!=min(CONDITIONS,key=lambda k:development[k]["development_priority"])
        or lineage.get("final_method_selected_by_new_development")!=selected):
        raise ValueError("Research candidate was selected using post-hoc blind results")
    cases=geometry.get("individual_GLBS")
    if (not isinstance(cases,list) or len(cases)!=288
        or geometry.get("source_blind_native_shapes")!=288
        or geometry.get("real_student_generated_GLBS")!=1152
        or geometry.get("original_validation_families")!=16
        or geometry.get("original_validation_archetypes")!=8):
        raise ValueError("288 source shapes or 1152 generated Kotlin GLBs incomplete")
    hashes=[r.get("original_glb_sha256") for r in cases]
    if (len(set(hashes))!=288
        or any(not isinstance(h,str) or len(h)!=64
               or any(c not in "0123456789abcdef" for c in h)
               for h in hashes)):
        raise ValueError("Repeated blind original GLB SHA or missing geometry source")
    sha=hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()
    if not (sha==geometry.get("source_hashes_sha256")
            ==report.get("blind_source_sha256")
            ==lineage.get("blind_source_sha256")):
        raise ValueError("Original source GLB checksums disagree")
    scores=geometry.get("results",{})
    predictions=report.get("blind_per_method_predictions",{})
    if set(scores)!=set(VARIANTS) or set(predictions)!=set(VARIANTS):
        raise ValueError("Missing matched parent, replay and physical learning GLB results")
    for name in VARIANTS:
        real=scores[name]
        observed=predictions[name]
        for left,right in (
            ("form_accuracy","form_accuracy"),
            ("operation_accuracy","operation_accuracy"),
            ("strength_mae","strength_mae"),
            ("predicted_distinct_forms","predicted_distinct_archetypes")):
            a=observed.get(left)
            b=real.get(right)
            if (not isinstance(a,(float,int)) or
                not isinstance(b,(float,int)) or
                not math.isfinite(a) or not math.isfinite(b) or
                abs(a-b)>.0002):
                raise ValueError("Neural student predictions mismatch actual original Kotlin GLBs")
        form_data=real.get("per_form",{})
        if (len(form_data)!=8 or any(x.get("count")!=36 for x in form_data.values())):
            raise ValueError("One or more original form classes absent from 3D audit")
    # All variants use exactly the same frozen shape identity. No oracle
    # ground-truth form can slip into a reconstruction arm.
    forms_inconsistent=0
    for case in cases:
        baseline=case["parent_v7_hard"]["form"]
        if any(case[condition]["form"]!=baseline for condition in CONDITIONS):
            forms_inconsistent+=1
    old=report.get("previous_training_retention_before",{})
    recalled=report.get("sessions",[])
    chosen_seeds=report.get("development_checkpoint_seeds",{})
    if (set(chosen_seeds)!=set(CONDITIONS)
        or any(chosen_seeds[k].get("seed") not in SEEDS
               or chosen_seeds[k].get("selected_step",0)<100
               for k in CONDITIONS)):
        raise ValueError("Development-selected seed and checkpoint provenance missing")
    matched=[x["old_training_retention"] for x in recalled
             if x["condition"]==selected
             and x["seed"]==chosen_seeds[selected]["seed"]
             and x["selected_development_step"]==
                 chosen_seeds[selected]["selected_step"]]
    if len(matched)!=1:
        raise ValueError("Old knowledge retention must match exact selected model")
    retained=matched[0]
    if any(not isinstance(x.get(field),(int,float)) or
           not math.isfinite(x[field]) for x in (old,retained)
           for field in ("operation_accuracy","strength_mae")):
        raise ValueError("No old-training continual-skill retention evidence")
    parent=scores["parent_v7_hard"]
    chosen=scores[selected]
    unchanged=geometry.get("unchanged_native_surface_chamfer",0)
    old_physical=parent["mean_3d_surface_chamfer"]
    new_physical=chosen["mean_3d_surface_chamfer"]
    replay=scores["supervised_replay"]["mean_3d_surface_chamfer"]
    if any(not isinstance(x,(int,float)) or not math.isfinite(x)
           or x<=0 for x in (old_physical,new_physical,unchanged,replay)):
        raise ValueError("Unbounded original real 3D mesh surface metric")
    gain=(old_physical-new_physical)/old_physical
    vs_replay=(replay-new_physical)/replay
    if abs(gain-geometry["physical_3d_gain_vs_generic_parent"][selected])>.0001:
        raise ValueError("Native source surface improvement arithmetic incorrect")
    # Strength-order stability across three new blind control values.
    inversions=0
    for fam in sorted({row["family"] for row in cases}):
        for op in lineage["ops"]:
            ordered=sorted(
                (x for x in cases
                 if x["family"]==fam and x["target_operation"]==op),
                key=lambda x:x["target_strength"])
            if len(ordered)!=3:raise ValueError("Missing a real blind strength sweep")
            inversions+=sum(
                a[selected]["strength"]>b[selected]["strength"]+.001
                for a,b in zip(ordered,ordered[1:]))
    checks={
        "old_native_operation_knowledge_retained":
            retained["operation_accuracy"]>=old["operation_accuracy"]-.02,
        "old_continuous_strength_knowledge_retained":
            retained["strength_mae"]<=old["strength_mae"]+.015,
        "blind_form_accuracy_at_least_75pct":
            chosen["form_accuracy"]>=.75,
        "all_eight_original_form_archetypes_predicted":
            chosen["predicted_distinct_archetypes"]==8,
        "four_or_more_distinct_actual_native_topologies":
            chosen["predicted_unique_triangle_topologies"]>=4,
        "no_generic_base_shell_collapse":
            chosen["generic_shell_output_count"]<=12,
        "all_variants_use_same_frozen_original_form_identity":
            forms_inconsistent==0,
        "blind_native_operation_accuracy_no_worse_than_parent":
            chosen["operation_accuracy"]>=parent["operation_accuracy"]-.012,
        "blind_native_strength_MAE_improved_by_at_least_point_015":
            chosen["strength_mae"]<=parent["strength_mae"]-.015,
        "real_3D_surface_improved_vs_old_student_at_least_8pct":
            gain>=.08,
        "real_3D_better_than_unmodified_correct_shape":
            new_physical<=unchanged,
        "native_geometry_objective_beats_equal_budget_replay":
            selected=="supervised_replay" or vs_replay>=.02,
        "ordered_strength_inversions_at_most_eight":
            inversions<=8,
        "all_real_1152_GLBS_and_new_source_hashes_passed":True,
        "no_Android_auto_promotion":True
    }
    return {
        "schema":"assetwright-real-form-conditioned-geometry-fidelity-research-gate-v8",
        "status":"eligible_for_human_research_review"
                 if all(checks.values())
                 else "experimental_checkpoint_not_promoted_parent_protected",
        "checks":checks,
        "development_selected_method":selected,
        "old_original_v6_weight_sha256":lineage["source_v6_weight_sha256"],
        "old_original_v7_identity_sha256":lineage["source_v7_form_weight_sha256"],
        "fresh_blind_source_sha256":sha,
        "real_optimizer_seconds":duration,
        "new_original_source_forms":288,
        "original_Kotlin_reconstructed_GLBS":1152,
        "frozen_shape_form_accuracy":chosen["form_accuracy"],
        "operation_recognition_before":parent["operation_accuracy"],
        "operation_recognition_after":chosen["operation_accuracy"],
        "strength_mae_before":parent["strength_mae"],
        "strength_mae_after":chosen["strength_mae"],
        "physical_3D_chamfer_parent":old_physical,
        "physical_3D_chamfer_after":new_physical,
        "physical_3D_chamfer_unchanged_form":unchanged,
        "physical_mesh_gain_vs_parent_fraction":gain,
        "physical_mesh_gain_vs_replay_fraction":vs_replay,
        "strength_order_reversals":inversions,
        "older_neural_weights_untouched":True,
        "human_review_required":True,
        "android_deployed":False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("evaluation","geometry","lineage","out"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    verdict=assess(
        json.loads(a.evaluation.read_text()),
        json.loads(a.geometry.read_text()),
        json.loads(a.lineage.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(verdict,indent=2)+"\n")
    print(json.dumps(verdict,indent=2))


if __name__=="__main__":
    main()

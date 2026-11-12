"""Fail-closed promotion gate for v12 *topology-matched* three-run research.

The training runs are REAL 300-second CPU gradient optimizations. The candidate
is preselected using 1,152 ORIGINAL DEVELOPMENT Kotlin GLBs. An independently
generated blind set of 1,152 *different* Kotlin GLBs measures true 3D accuracy.
Neither a successful workflow nor saved weights constitutes deployment.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from native_resolution_aware_v12 import (
    SCHEMA,WEIGHT_SCHEMA,STUDY_NAME,CONDITIONS,VARIANTS,SEEDS)
from native_resolution_aware_forward_audit import SCHEMA as FORWARD
from select_native_resolution_aware_v12 import select


def assess(report,dev,selection,blind,lineage):
    if (report.get("schema")!=SCHEMA
        or report.get("study")!=STUDY_NAME
        or lineage.get("schema")!=WEIGHT_SCHEMA
        or blind.get("schema")!=FORWARD
        or blind.get("study_id")!=STUDY_NAME
        or blind.get("evaluated_split")!="validation"
        or dev.get("evaluated_split")!="development"
        or selection!=select(report,dev,lineage)):
        raise ValueError("Source-hashed source or development-only selection disagrees")
    if (report.get("development_selected")!=selection["selected"]
        or lineage.get("final_method_selected_by_new_development")!=selection["selected"]
        or lineage.get("model_chosen_on_real_development_Kotlin_GLBS") is not True
        or report.get("development_selection_source")!=selection["schema"]
        or selection.get("selected_without_blind_3D_audit") is not True):
        raise ValueError("Method or seed was selected using blind rather than real development GLBs")
    required=(
        report.get("old_v10_trained_adapter_sha256")==
            lineage.get("source_v10_adapter_sha256")
        and report.get("old_v9_form_checkpoint_sha256")==
            lineage.get("source_v9_identity_sha256")
        and report.get("actual_original_v10_geometry_checkpoint_warm_started") is True
        and lineage.get("v10_geometry_weights_warm_started") is True
        and lineage.get("v9_form_head_weights_frozen") is True
        and lineage.get("legacy_action_weights_frozen") is True
        and report.get("older_correct_original_train_sources")==1152
        and report.get("new_original_shape_train_examples")==1152
        and report.get("new_development_examples")==288
        and report.get("new_fresh_unseen_blind_examples")==288
        and report.get("new_shape_train_families")==48
        and report.get("fresh_blind_form_families")==16
        and report.get("three_equal_short_CPU_runs") is True
        and report.get("source_baseline_topology_available_at_inference") is True
        and report.get("geometry_supervision_only_original_kotlin_GLBS") is True
        and report.get("external_teacher_used") is False
        and report.get("android_neural_deployed") is False
        and lineage.get("not_approved_for_android") is True)
    if not required:
        raise ValueError("The ORIGINAL trained geometry model was reset, leaked, or depolyed")
    if (report.get("configured_optimizer_seconds")!=900
        or not 900<=report.get("measured_optimizer_seconds",0)<=1050
        or report.get("completed_sessions")!=3):
        raise ValueError("Three real 300-second CPU training sessions not proven")
    sessions=report.get("sessions",[])
    if (len(sessions)!=3
        or {(x.get("condition"),x.get("seed")) for x in sessions}
            !={(x,1) for x in CONDITIONS}
        or any(x.get("actual_optimizer_seconds",0)<299
               or x.get("optimizer_updates",0)<100
               or x.get("selected_development_step",0)<100
               for x in sessions)):
        raise ValueError("Three genuine independently trained neural adapters missing")
    if (blind.get("source_blind_native_shapes")!=288
        or blind.get("real_student_generated_GLBS")!=1152
        or blind.get("original_validation_families")!=16
        or blind.get("original_validation_archetypes")!=8
        or blind.get("all_source_and_reconstructed_meshes_valid") is not True
        or blind.get("input_resolution_verified_from_unmodified_GLBS") is not True
        or blind.get("external_meshes_used") is not False):
        raise ValueError("1,152 original blind native topology-matched GLBs not verified")
    cases=blind.get("individual_GLBS")
    if not isinstance(cases,list) or len(cases)!=288:
        raise ValueError("Unseen original source geometry was not scored")
    source_hashes=[r.get("original_glb_sha256") for r in cases]
    if len(set(source_hashes))!=288:
        raise ValueError("Repeated original blind source hashes")
    calculated=hashlib.sha256(
        "\n".join(sorted(source_hashes)).encode()).hexdigest()
    if (calculated!=blind.get("source_hashes_sha256")
        or calculated!=report.get("blind_source_sha256")
        or calculated!=lineage.get("blind_source_sha256")
        or calculated==dev.get("source_hashes_sha256")):
        raise ValueError("Original unseen blind GLB source was leaked or replaced")
    rows=blind.get("results",{})
    predictions=report.get("blind_per_method_predictions",{})
    if set(rows)!=set(VARIANTS) or set(predictions)!=set(VARIANTS):
        raise ValueError("Missing exact four comparable original model checkpoints")
    for name in VARIANTS:
        source=rows[name]
        stats=predictions[name]
        for key,key2 in (("form_accuracy","form_accuracy"),
                         ("operation_accuracy","operation_accuracy"),
                         ("strength_mae","strength_mae"),
                         ("predicted_distinct_archetypes","predicted_distinct_forms")):
            if abs(source[key]-stats[key2])>.0002:
                raise ValueError("Neural predictions disagreed with real Kotlin geometry")
        if (len(source["per_form"])!=8
            or any(v["count"]!=36 for v in source["per_form"].values())):
            raise ValueError("Eight original source archetypes not balanced")
    for r in cases:
        orig=r["parent_v10"]["form"]
        if any(r[k]["form"]!=orig for k in CONDITIONS if k in r):
            raise ValueError("Neural form identity was changed between comparison arms")
        if any(r[k]["form"]!=orig for k in VARIANTS[1:]):
            raise ValueError("Frozen shape recognition changed between arms")
        if any(r[k]["triangles"]!=r["original_mesh_triangles"]
               for k in VARIANTS):
            raise ValueError("A model reconstructed at a different or oracle target topology")
    parent=rows["parent_v10"]
    chosen=rows[selection["selected"]]
    older=report.get("previous_training_retention_before",{})
    retained=[x["old_training_retention"] for x in sessions
              if x["condition"]==selection["selected"].removesuffix("_stage1")]
    if len(retained)!=1:
        raise ValueError("No retained previous skill from selected neural run")
    past=retained[0]
    before=parent["mean_3d_surface_chamfer"]
    after=chosen["mean_3d_surface_chamfer"]
    unchanged=blind["unchanged_native_surface_chamfer"]
    if not 0<before<1 or not 0<after<1 or not 0<unchanged<1:
        raise ValueError("Invalid original physical 3D scale")
    gain=(before-after)/before
    inversions=0
    for family in {x["family"] for x in cases}:
        for op in lineage["ops"]:
            ordered=sorted(
                (x for x in cases if x["family"]==family
                 and x["target_operation"]==op),
                key=lambda x:x["target_strength"])
            if len(ordered)!=3:
                raise ValueError("Original strength sweep incomplete")
            inversions+=sum(
                x[selection["selected"]]["strength"]>
                y[selection["selected"]]["strength"]+.001
                for x,y in zip(ordered,ordered[1:]))
    checks={
        "no_original_operation_forgetting":
            past["operation_accuracy"]>=older["operation_accuracy"]-.025,
        "no_original_strength_forgetting":
            past["strength_mae"]<=older["strength_mae"]+.02,
        "eight_real_original_shape_classes":
            chosen["form_accuracy"]>=.90 and
            chosen["predicted_distinct_archetypes"]==8,
        "no_generic_shell_collapse":
            chosen["generic_shell_output_count"]==0,
        "blind_operation_accuracy_not_worse":
            chosen["operation_accuracy"]>=parent["operation_accuracy"]-.015,
        "blind_strength_MAE_improved":
            chosen["strength_mae"]<=parent["strength_mae"]-.01,
        "real_topology_matched_3D_chamfer_gain_at_least_3pct":
            gain>=.03,
        "real_3D_model_better_than_unmodified_correct_input":
            after<=unchanged,
        "native_mesh_resolution_match_for_all_GLBS":True,
        "ordered_strength_inversions_at_most_eight":
            inversions<=8,
        "development_selected_on_actual_1152_native_GLBS":True,
        "all_1152_blind_GLBS_and_digests_valid":True,
        "no_Android_auto_promotion":True
    }
    return {
        "schema":"assetwright-v12-resolution-aware-true-native-geometry-gate",
        "status":"eligible_for_human_research_review"
                if all(checks.values()) else "research_only_rejected_parent_protected",
        "checks":checks,
        "selected_on_development_3D_only":selection["selected"],
        "development_physical_gain":selection["physical_development_gain_vs_parent_fraction"],
        "frozen_parent_weight_sha256":lineage["source_v10_adapter_sha256"],
        "frozen_identity_weight_sha256":lineage["source_v9_identity_sha256"],
        "measured_real_CPU_training_seconds":report["measured_optimizer_seconds"],
        "independent_development_real_Kotlin_GLBS":1152,
        "blind_new_original_Kotlin_GLBS":1152,
        "old_operation_accuracy":parent["operation_accuracy"],
        "new_operation_accuracy":chosen["operation_accuracy"],
        "old_strength_MAE":parent["strength_mae"],
        "new_strength_MAE":chosen["strength_mae"],
        "old_chamfer":before,
        "new_chamfer":after,
        "unchanged_correct_source_chamfer":unchanged,
        "blind_real_native_3D_gain_fraction":gain,
        "strength_order_reversals":inversions,
        "all_previous_knowledge_preserved":True,
        "android_neural_deployed":False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("evaluation","development_geometry","selection","blind_geometry","lineage","out"):
        p.add_argument("--"+k.replace("_","-"),type=Path,required=True)
    a=p.parse_args()
    e=json.loads(a.evaluation.read_text())
    d=json.loads(a.development_geometry.read_text())
    s=json.loads(a.selection.read_text())
    b=json.loads(a.blind_geometry.read_text())
    l=json.loads(a.lineage.read_text())
    result=assess(e,d,s,b,l)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()

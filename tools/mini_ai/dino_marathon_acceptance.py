"""Reject any long-run Mini AI that fails real native GLB or strength checks.

The research must prove 32 minutes of REAL optimization, source hash alignment
with 96 NEW blind native meshes, and improvement over same-budget teacher-free
students. Never deploy a checkpoint to Android.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from dino_marathon_student import STUDENT_SCHEMA,EVALUATION_SCHEMA,SEEDS


def reconcile(visual,geometry,student):
    if (visual.get("schema")!=EVALUATION_SCHEMA or
        geometry.get("schema")!="assetwright-native-before-after-forward-audit-v1" or
        geometry.get("study_id")!="strength_marathon_v3" or
        student.get("schema")!=STUDENT_SCHEMA):
        raise ValueError("Unknown research model or source-mesh evidence")
    if (visual.get("original_meshes")!=888 or
        visual.get("original_before_after_changes")!=864 or
        visual.get("train_examples")!=672 or
        visual.get("development_examples")!=96 or
        visual.get("untouched_holdout_examples")!=96 or
        visual.get("independent_seeds_per_condition")!=8 or
        visual.get("completed_independent_training_sessions")!=16 or
        geometry.get("fresh_original_target_glbs")!=96 or
        geometry.get("real_student_generated_glbs")!=192 or
        geometry.get("native_unmodified_family_baselines")!=4):
        raise ValueError("Incomplete or incorrectly partitioned native marathon")
    seconds=float(visual.get("verified_active_training_seconds",-1))
    if (not math.isfinite(seconds) or seconds<1800 or seconds>2400 or
        visual.get("requested_active_training_seconds")!=1920):
        raise ValueError("Insufficient verified real CPU optimization time")
    sessions=visual.get("all_session_development_results",{})
    for condition in ("teacher_free","DINO_guided"):
        history=sessions.get(condition)
        if (not isinstance(history,list) or len(history)!=8 or
            {r.get("seed") for r in history}!=set(SEEDS) or
            any(r.get("session_training_elapsed_seconds",0)<105 or
                r.get("selected_dev_step",0)<=0 or
                r.get("optimizer_updates",0)<=0 for r in history) or
            sessions.get(condition+"_winner_seed") not in SEEDS):
            raise ValueError("Missing independent active gradient-optimization sessions")
    if (student.get("original_native_generator")!="AssetWright-Kotlin-AdvancedFormLab" or
        student.get("teacher_needed_at_inference") is not False or
        student.get("teacher_generates_geometry") is not False or
        student.get("android_deployable") is not False or
        student.get("approved_for_generation") is not False or
        visual.get("teacher_generates_geometry") is not False or
        visual.get("teacher_needed_at_inference") is not False or
        geometry.get("all_native_glbs_structurally_audited") is not True or
        geometry.get("external_AI_used_to_generate_meshes") is not False):
        raise ValueError("Teacher or Android deployment safety boundary violated")
    raw=geometry.get("cases")
    if not isinstance(raw,list) or len(raw)!=96:
        raise ValueError("Missing independently reconstructed geometry")
    digests=[x.get("source_glb_sha256") for x in raw]
    if (len(set(digests))!=96 or any(
        not isinstance(h,str) or len(h)!=64 or
        any(c not in "0123456789abcdef" for c in h) for h in digests)):
        raise ValueError("Repeated or unverified native geometry sources")
    hash_id=hashlib.sha256("\n".join(sorted(digests)).encode()).hexdigest()
    if (hash_id!=geometry.get("source_hashes_sha256") or
        hash_id!=visual.get("source_validation_hashes_sha256") or
        hash_id!=student.get("blind_source_hashes_sha256")):
        raise ValueError("Actual forward GLBs mismatch supervised blind source hashes")
    metrics=visual.get("heldout",{})
    for key,mapping in (("teacher_free","paired_teacher_free"),
                        ("DINO_guided","paired_with_DINO")):
        predicted=metrics.get(key,{})
        audited=geometry.get(mapping,{})
        for stat,ground in (("accuracy","operation_accuracy"),
                            ("strength_mae","strength_mae")):
            a=float(predicted.get(stat,-1))
            b=float(audited.get(ground,-2))
            if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>.0002:
                raise ValueError("Forward native GLB comparison contradicts student metrics")
    with_teacher=metrics["DINO_guided"]
    control=metrics["teacher_free"]
    gain=(control["strength_mae"]-with_teacher["strength_mae"])/control["strength_mae"]
    if abs(gain-visual.get("teacher_strength_gain_fraction",-1))>1.e-4:
        raise ValueError("Unverified numeric teacher-strength effect")
    per_op=with_teacher.get("per_operation",{})
    if set(per_op)!=set(student.get("supported_ops",())) or len(per_op)!=6:
        raise ValueError("Incomplete original six-operation strength school")
    if any(x.get("total")!=16 for x in per_op.values()):
        raise ValueError("Incomplete four-family independent operation balance")
    worst=max(float(x["strength_mae"]) for x in per_op.values())
    inversion=0
    for family in sorted({case["family"] for case in raw}):
        for op in per_op:
            examples=sorted(
                [x for x in raw if x["family"]==family and
                 x["target_operation"]==op],key=lambda x:x["target_strength"])
            if len(examples)!=4: raise ValueError("Missing native controlled-strength sweep")
            inversion+=sum(examples[i+1]["DINO_guided"]["strength"]+.001 <
                           examples[i]["DINO_guided"]["strength"] for i in range(3))
    native_gain=float(geometry.get("improvement_over_unchanged_native_fraction",-1))
    teacher_geometry_gain=float(
        geometry.get("DINO_improvement_over_paired_without_teacher_fraction",-1))
    if not all(math.isfinite(x) for x in (native_gain,teacher_geometry_gain,worst)):
        raise ValueError("Unbounded independent geometry improvement")
    checks={
        "true_32min_gradient_sessions":True,
        "actual_original_Kotlin_reconstructions":True,
        "operation_accuracy_ge_65pct":with_teacher["accuracy"]>=.65,
        "strength_MAE_le_point18":with_teacher["strength_mae"]<=.18,
        "each_operator_strength_MAE_le_point30":worst<=.30,
        "DINO_strength_beats_equal_budget_control_by_point008":
            with_teacher["strength_mae"]<=control["strength_mae"]-.008,
        "DINO_classification_not_degraded":
            with_teacher["accuracy"]>=control["accuracy"]-.03,
        "native_geometry_beats_unmodified_by_10pct":native_gain>=.10,
        "native_geometry_beats_teacher_free_by_2pct":teacher_geometry_gain>=.02,
        "monotonic_strength_violations_le_four":inversion<=4,
        "hashes_and_geometry_independently_audited":True,
        "Android_and_teacher_execution_blocked":True
    }
    pass_research=all(checks.values())
    return {
        "schema":"assetwright-32min-long-run-final-native-acceptance-v3",
        "status":"eligible_for_human_research_review" if pass_research else "research_candidate_rejected",
        "checks":checks,"measured_training_seconds":seconds,
        "completed_training_sessions":16,
        "new_holdout_native_source_targets":96,
        "actual_own_Kotlin_reconstructed_glbs":192,
        "guided_operation_accuracy":with_teacher["accuracy"],
        "guided_strength_MAE":with_teacher["strength_mae"],
        "teacher_free_strength_MAE":control["strength_mae"],
        "native_improvement_over_unchanged":native_gain,
        "DINO_improvement_vs_teacher_free_geometry":teacher_geometry_gain,
        "heldout_monotonic_order_violations":inversion,
        "never_auto_deploy_to_Android":True,
        "human_visual_approval_required":True
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("visual","forward","checkpoint","out"):
        p.add_argument("--"+key,required=True,type=Path)
    a=p.parse_args()
    report=reconcile(json.loads(a.visual.read_text()),
                     json.loads(a.forward.read_text()),
                     json.loads(a.checkpoint.read_text()))
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"combined_disposition.json").write_text(json.dumps(report,indent=2)+"\n")
    human_review=a.out/"validated_research_student.json"
    human_review.unlink(missing_ok=True)
    if report["status"]=="eligible_for_human_research_review":
        human_review.write_text(a.checkpoint.read_text())
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()

"""Research-only multi-session strength calibration and native GLB accept gate.

Requires the SAME new 96 heldout source GLB hashes, matching actual Kotlin
predictions, valid topology and genuine improvement over teacher-free.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from dino_strength_student import RESULT_SCHEMA,SCHEMA


def reconcile(visual:dict,forward:dict,checkpoint:dict)->dict:
    if (visual.get("schema")!=RESULT_SCHEMA
        or forward.get("schema")!="assetwright-native-before-after-forward-audit-v1"
        or forward.get("study_id")!="strength_v2"
        or checkpoint.get("schema")!=SCHEMA):
        raise ValueError("Untrusted multi-session calibration evidence")
    if (visual.get("training_examples")!=756
        or visual.get("development_examples")!=96
        or visual.get("untouched_validation_examples")!=96
        or visual.get("independent_seeds_per_condition")!=8
        or visual.get("total_independent_training_sessions")!=16
        or forward.get("fresh_original_target_glbs")!=96
        or forward.get("real_student_generated_glbs")!=192
        or forward.get("native_unmodified_family_baselines")!=4):
        raise ValueError("Incomplete independent calibration cohort or sessions")
    hashes=forward.get("cases")
    if not isinstance(hashes,list) or len(hashes)!=96:
        raise ValueError("Missing actual source-matched native GLB cases")
    original_hashes=[r.get("source_glb_sha256") for r in hashes]
    if any(not isinstance(h,str) or len(h)!=64 or
           any(ch not in "0123456789abcdef" for ch in h) for h in original_hashes):
        raise ValueError("Invalid original Kotlin source hashes")
    if len(set(original_hashes))!=96:
        raise ValueError("Repeated source geometry in final validation")
    digest=hashlib.sha256("\n".join(sorted(original_hashes)).encode()).hexdigest()
    if (digest!=visual.get("source_modified_sha256_validation")
        or digest!=forward.get("source_hashes_sha256")
        or digest!=checkpoint.get("source_hash_validation")):
        raise ValueError("Mismatch between image/student/native source GLB hashes")
    if (checkpoint.get("owned_generator")!="AssetWright-Kotlin-AdvancedFormLab"
        or checkpoint.get("teacher_needed_at_inference") is not False
        or checkpoint.get("android_deployable") is not False
        or checkpoint.get("approved_for_geometry_generation") is not False
        or forward.get("all_native_glbs_structurally_audited") is not True
        or forward.get("external_AI_used_to_generate_meshes") is not False
        or visual.get("external_AI_produces_3d") is not False
        or visual.get("teacher_used_during_inference") is not False):
        raise ValueError("Unsafe teacher/native generator or mobile runtime boundary")
    source_metrics=visual.get("heldout",{})
    for name,which in (("teacher_free","paired_teacher_free"),
                       ("DINO_guided","paired_with_DINO")):
        pixels=source_metrics.get(name,{})
        shape=forward.get(which,{})
        for a,b in (("accuracy","operation_accuracy"),("strength_mae","strength_mae")):
            x=float(pixels.get(a,-1))
            y=float(shape.get(b,-2))
            if not math.isfinite(x) or not math.isfinite(y) or abs(x-y)>.0002:
                raise ValueError("Native GLB and frozen student scores disagree")

    guided=source_metrics["DINO_guided"]
    pure=source_metrics["teacher_free"]
    gain_mae=float(visual.get("DINO_strength_error_reduction_fraction",-1))
    gain_glb=float(forward.get("DINO_improvement_over_paired_without_teacher_fraction",-1))
    gain_native=float(forward.get("improvement_over_unchanged_native_fraction",-1))
    if not all(math.isfinite(v) for v in (gain_mae,gain_glb,gain_native)):
        raise ValueError("Invalid native strength/generalization metrics")
    expected_gain=(pure["strength_mae"]-guided["strength_mae"])/pure["strength_mae"]
    if abs(expected_gain-gain_mae)>.0001:
        raise ValueError("Unreconciled original student strength gain")

    # Expose any single native operation whose strength remains unreliable.
    per_op=guided.get("per_operator",{})
    if set(per_op)!=set(checkpoint.get("supported_operations",[])) or len(per_op)!=6:
        raise ValueError("Missing native operation-level calibration")
    worst_strength=max(float(v["strength_mae"]) for v in per_op.values())
    if any(v.get("total")!=16 for v in per_op.values()):
        raise ValueError("Heldout operation-family balance violated")

    monotonic={}
    for family in sorted({row["family"] for row in hashes}):
        for op in sorted(per_op):
            samples=sorted((row for row in hashes
                            if row["family"]==family and row["target_operation"]==op),
                           key=lambda row:row["target_strength"])
            if len(samples)!=4: raise ValueError("Missing independent strength sweep")
            monotonic[(family,op)]=sum(
                samples[i+1]["DINO_guided"]["strength"]+.001 <
                samples[i]["DINO_guided"]["strength"]
                for i in range(3))
    monotonic_violations=sum(monotonic.values())

    checks={
        "classification_accuracy_ge_0_65":guided["accuracy"]>=.65,
        "continuous_strength_MAE_le_0_18":guided["strength_mae"]<=.18,
        "per_operation_strength_MAE_le_0_30":worst_strength<=.30,
        "guided_strength_gain_at_least_0_008_absolute":
            guided["strength_mae"]<=pure["strength_mae"]-.008,
        "teacher_does_not_hurt_classification":guided["accuracy"]>=pure["accuracy"]-.03,
        "real_GLB_gain_over_unchanged_ge_10pct":gain_native>=.10,
        "real_GLB_gain_over_teacher_free_ge_2pct":gain_glb>=.02,
        "monotonic_strength_consistency":monotonic_violations<=4,
        "source_and_forward_audits_match":True,
        "inference_teacher_free":True,
        "Android_release_blocked":True
    }
    approved=all(checks.values())
    return {
        "schema":"assetwright-original-strength-multisession-final-gate-v2",
        "status":"eligible_for_human_research_review" if approved else "research_candidate_not_approved",
        "checks":checks,
        "eight_independent_sessions_per_group":True,
        "new_blind_native_targets":96,
        "real_generated_Kotlin_reconstructions":192,
        "guided_operation_accuracy":guided["accuracy"],
        "guided_strength_MAE":guided["strength_mae"],
        "teacher_free_strength_MAE":pure["strength_mae"],
        "DINO_strength_error_reduction_fraction":gain_mae,
        "real_vertex_improvement_over_unchanged_fraction":gain_native,
        "real_vertex_improvement_vs_no_teacher_fraction":gain_glb,
        "worst_operation_strength_MAE":worst_strength,
        "monotonic_violations_of_72_adjacent_pairs":monotonic_violations,
        "human_visual_review_required":True,
        "Android_deployable":False,
        "automatic_promotion":False,
        "teacher_generates_meshes":False
    }


def run(visual:Path,forward:Path,checkpoint:Path,out:Path)->dict:
    result=reconcile(json.loads(visual.read_text()),
                     json.loads(forward.read_text()),
                     json.loads(checkpoint.read_text()))
    out.mkdir(parents=True,exist_ok=True)
    (out/"final_research_disposition.json").write_text(json.dumps(result,indent=2)+"\n")
    eligible=out/"validated_research_student.json"
    eligible.unlink(missing_ok=True)
    if result["status"]=="eligible_for_human_research_review":
        eligible.write_text(checkpoint.read_text())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("visual","forward","checkpoint","out"):
        p.add_argument("--"+key,required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(run(a.visual,a.forward,a.checkpoint,a.out),indent=2))


if __name__=="__main__":
    main()

"""Fail-closed gate: both image learning AND original native GLB construction.

No app weight mutation, no third-party 3D generation, no automatic promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path


def gate(visual:dict,forward:dict,model:dict)->dict:
    if (visual.get("schema")!="assetwright-native-before-after-visual-comparison-v1"
        or forward.get("schema")!="assetwright-native-before-after-forward-audit-v1"
        or model.get("schema")!="assetwright-original-before-after-native-student-v1"):
        raise ValueError("Unexpected original native before/after evidence")
    if (visual.get("fresh_validation_examples")!=54
        or forward.get("fresh_original_target_glbs")!=54
        or forward.get("real_student_generated_glbs")!=108
        or visual.get("original_kotlin_glbs")!=486
        or visual.get("native_before_after_pairs")!=468):
        raise ValueError("Incomplete original independent heldout study")
    if (visual.get("heldout_modified_source_hashes_sha256")!=
            forward.get("source_hashes_sha256")):
        raise ValueError("Image student and actual GLB evaluation have different source hashes")
    if (model.get("generator_authority")!="AssetWright-Kotlin-AdvancedFormLab"
        or model.get("teacher_required_at_inference") is not False
        or model.get("android_deployable") is not False
        or model.get("approved_for_geometry_generation") is not False
        or forward.get("all_native_glbs_structurally_audited") is not True
        or visual.get("model_inference_requires_DINO") is not False
        or visual.get("external_AI_generates_3d") is not False
        or forward.get("external_AI_used_to_generate_meshes") is not False):
        raise ValueError("Unsafe outside-model or production approval boundary")
    vm=visual.get("metrics",{})
    for name,which in (("paired_without_DINO","paired_teacher_free"),
                       ("paired_with_DINO","paired_with_DINO")):
        v=vm.get(name,{})
        f=forward.get(which,{})
        for a,b in (("accuracy","operation_accuracy"),("strength_mae","strength_mae")):
            value=float(v.get(a,-1))
            actual=float(f.get(b,-2))
            if not math.isfinite(value) or not math.isfinite(actual) or abs(value-actual)>.0002:
                raise ValueError("Visual and reconstructed native operator predictions disagree")
    main=vm["paired_with_DINO"]
    pair_gain=float(visual.get("before_after_joint_improvement_fraction",-1))
    teacher_gain=float(visual.get("DINO_joint_improvement_vs_paired",-1))
    error_gain=float(forward.get("improvement_over_unchanged_native_fraction",-1))
    vs_no_teacher=float(forward.get("DINO_improvement_over_paired_without_teacher_fraction",-1))
    if not all(math.isfinite(v) for v in
               (pair_gain,teacher_gain,error_gain,vs_no_teacher)):
        raise ValueError("Invalid native and visual improvement reports")
    checks={
        "visual_pair_improves_after_only":pair_gain>=.05,
        "DINO_heldout_visual_gain":teacher_gain>=.025,
        "native_operator_accuracy":main["accuracy"]>=.60,
        "native_strength_mae":main["strength_mae"]<=.18,
        "real_GLBS_improve_over_unchanged":error_gain>=.10,
        "DINO_improves_real_GLBS_over_no_teacher":vs_no_teacher>=.02,
        "independent_native_audit_pass":forward.get("status")=="forward_reconstruction_pass",
        "independent_visual_transfer_pass":visual.get("status")=="provisional_visual_transfer_pass",
        "matching_source_hashes":True,
        "non_Android_research_only":True
    }
    eligible=all(checks.values())
    return {
        "schema":"assetwright-native-before-after-combined-gate-v1",
        "status":"eligible_for_human_research_review" if eligible else "research_candidate_not_approved",
        "checks":checks,
        "original_Kotlin_source_pairs":468,
        "fresh_heldout_source_shapes":54,
        "native_reconstructed_student_glbs":108,
        "DINO_visual_joint_gain":teacher_gain,
        "guided_operation_accuracy":main["accuracy"],
        "guided_strength_mae":main["strength_mae"],
        "guided_native_vertex_gain_over_unchanged":error_gain,
        "guided_native_vertex_gain_over_teacher_free":vs_no_teacher,
        "teacher_required_at_inference":False,
        "android_deployable":False,
        "automatic_promotion":False,
        "human_visual_review_required":True,
        "note":"Even passing research metrics never auto-deploys or proves broad image-to-3D."
    }


def run(visual_file:Path,forward_file:Path,model_file:Path,out:Path)->dict:
    visual=json.loads(visual_file.read_text())
    forward=json.loads(forward_file.read_text())
    candidate=json.loads(model_file.read_text())
    result=gate(visual,forward,candidate)
    out.mkdir(parents=True,exist_ok=True)
    (out/"combined_disposition.json").write_text(json.dumps(result,indent=2)+"\n")
    checked=out/"validated_research_student.json"
    checked.unlink(missing_ok=True)
    if result["status"]=="eligible_for_human_research_review":
        checked.write_text(json.dumps(candidate,separators=(",",":"))+"\n")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("visual","forward","model","out"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(run(a.visual,a.forward,a.model,a.out),indent=2))


if __name__=="__main__":
    main()

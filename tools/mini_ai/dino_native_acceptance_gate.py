"""Reconcile teacher transfer with REAL reconstructed GLB quality before acceptance.

A good DINO embedding or pixel classification score alone NEVER authorizes a
native shape generator. Do not copy results into Android or use outside meshes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def disposition(visual:dict,forward:dict,student:dict)->dict:
    if (visual.get("schema")!="assetwright-original-geometry-dino-visual-study-v1"
        or forward.get("schema")!="assetwright-dino-original-forward-native-glb-audit-v1"
        or student.get("schema")!="assetwright-owned-image-native-operator-student-v1"):
        raise ValueError("Unrecognized original visual/native source evidence")
    if (visual.get("official_unseen_native_glbs")!=36
        or forward.get("actual_original_target_glbs")!=36
        or forward.get("actual_student_reconstructed_glbs")!=36
        or forward.get("actual_constant_baseline_glbs")!=36):
        raise ValueError("Incomplete original native comparison")
    cases=forward.get("cases",[])
    if not isinstance(cases,list) or len(cases)!=36:
        raise ValueError("Missing independent, source-hashed reconstruction evidence")
    digests=[r.get("target_source_sha256") for r in cases]
    if any(not isinstance(h,str) or len(h)!=64
           or any(c not in "0123456789abcdef" for c in h) for h in digests):
        raise ValueError("Unverified native original geometry hashes")
    if len(set(digests))!=36:
        raise ValueError("Repeated original source geometry")
    expected=hashlib.sha256("\n".join(sorted(digests)).encode()).hexdigest()
    if visual.get("heldout_source_sha256")!=expected:
        raise ValueError("Visual classifier and forward geometry used different GLBs")
    metrics=visual.get("teacher_distilled_student",{})
    if (abs(float(metrics.get("accuracy",-1))-
            float(forward.get("predicted_operator_accuracy",-2)))>1.e-5 or
        abs(float(metrics.get("strength_mae",-1))-
            float(forward.get("predicted_strength_mae",-2)))>.0002):
        raise ValueError("Visual student and actual GLB prediction metrics disagree")
    if (visual.get("teacher_generates_3d") is not False
        or visual.get("pixel_student_requires_teacher_at_inference") is not False
        or forward.get("external_ai_meshes_used") is not False
        or forward.get("all_meshes_independently_structurally_valid") is not True
        or student.get("teacher_runtime_required") is not False
        or student.get("android_deployable") is not False
        or student.get("approved_for_geometry_generation") is not False):
        raise ValueError("Unsafe native GLB production boundary")
    checks={
        "validated_on_heldout_visual_transfer":
            visual.get("status")=="validated_research_visual_to_native",
        "independent_forward_geometry_gate":
            forward.get("strict_forward_geometry_gate") is True,
        "all_real_target_and_reconstruction_meshes_valid":
            forward["all_meshes_independently_structurally_valid"] is True,
        "source_hash_and_prediction_metrics_agree": True,
        "teacher_not_used_at_inference":True,
        "not_Android_deployed":True
    }
    accepted=all(checks.values())
    return {
        "schema":"assetwright-dino-visual-native-combined-disposition-v1",
        "status":"eligible_for_human_research_review" if accepted else "research_candidate_rejected",
        "checks":checks,
        "visual_operation_accuracy":metrics["accuracy"],
        "visual_strength_mae":metrics["strength_mae"],
        "actual_native_vertex_improvement_fraction":forward["forward_improvement_fraction"],
        "native_geometry_valid":True,
        "android_deployable":False,
        "automatic_geometry_generation_approval":False,
        "human_approval_required":True,
        "note":"Research checkpoint is never installed into Android. Provenance and both task gates must pass before *human* research review."
    }


def run(evaluation:Path,forward:Path,candidate:Path,out:Path)->dict:
    visual=json.loads(evaluation.read_text())
    geometry=json.loads(forward.read_text())
    model=json.loads(candidate.read_text())
    answer=disposition(visual,geometry,model)
    out.mkdir(parents=True,exist_ok=True)
    (out/"combined_disposition.json").write_text(json.dumps(answer,indent=2)+"\n")
    validated=out/"validated_research_student.json"
    validated.unlink(missing_ok=True)
    if answer["status"]=="eligible_for_human_research_review":
        # Research-only. Never auto-promote to app or native model generator.
        validated.write_text(json.dumps(model,separators=(",",":"))+"\n")
    return answer


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ("evaluation","forward","candidate","out"):
        parser.add_argument("--"+k,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.evaluation,args.forward,args.candidate,args.out),indent=2))


if __name__=="__main__":
    main()

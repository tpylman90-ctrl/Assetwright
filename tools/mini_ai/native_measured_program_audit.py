"""Independent forward geometry gate for an OWN learned inverse program.

Compare new original GLB outputs against the held-out measured target GLBs.
A source SHA check is required on every file. Evaluation detects numerical
geometry differences and manifold defects, NOT aesthetics/automotive welds.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from native_measured_inverse import (
    SCHEMA as RESPONSE, ORDER, METRIC, case, digest, target_delta,
)
from generated_glb_critic import inspect

SCHEMA="assetwright-native-measured-multi-op-geometry-audit-v1"
TOLERANCE={
    "recess_rear_socket":.04,          # meters
    "sculpt_cockpit_shoulder":.035,     # meters
    "loft_rear_nacelle":.13,           # dimensionless flare ratio
}

def compare(target:dict,predicted:dict,op:str)->dict:
    field=METRIC[op]
    error=abs(target["metrics"][field]-predicted["metrics"][field])
    if target["meta"].get("phase")!="reference" or predicted["meta"].get("phase")!="predicted":
        raise ValueError("Invalid source reference to generated target distinction")
    meta=predicted["meta"]
    if not isinstance(meta.get("model_sha256"),str) or len(meta["model_sha256"])!=64:
        raise ValueError("Missing owned student weights provenance")
    if (predicted["structural"]["nonmanifold_edges"]!=0 or
        predicted["structural"]["invalid_triangles"]!=0 or
        predicted["structural"]["triangles"]>12000):
        raise ValueError("Non-manifold or excessive original geometry")
    return {"metric":field,"target":target["metrics"][field],
            "generated":predicted["metrics"][field],
            "absolute_error":round(error,6),
            "allowed_error":TOLERANCE[op],
            "passed":error<=TOLERANCE[op]}

def audit(reference_folder:Path,predicted_folder:Path,report_file:Path)->dict:
    report=json.loads(report_file.read_text())
    if report.get("schema")!=RESPONSE or report.get("research_status")!="verified_inverse_geometry_response":
        raise ValueError("Inverse model did not pass independent target-strength gate")
    actual_order=[p.get("operation") for p in report["learned_construction_program"]]
    if tuple(actual_order)!=ORDER:
        raise ValueError("Incorrect owned construction-operation sequence")
    ref_baseline=case(reference_folder,"measure__blindfamily__baseline")
    checks={}
    source_model_sha=report["source_checkpoint_sha256"]
    for item in report["learned_construction_program"]:
        op=item["operation"]
        reference=case(reference_folder,"measure__blindfamily__"+op+"__s725")
        predicted=case(predicted_folder,"predicted__blindfamily__"+op)
        if predicted["meta"].get("model_sha256")!=source_model_sha:
            raise ValueError("Owned source checkpoint hashes do not match")
        commands=predicted["meta"].get("commands")
        if len(commands)!=1 or commands[0]["operation"]!=op or abs(
                commands[0]["strength"]-item["strength"])>.00001:
            raise ValueError("Native output does not implement predicted operation")
        checks[op]=compare(reference,predicted,op)
    combined_reference=case(reference_folder,"measure__blindfamily__program_target")
    combined_prediction=case(predicted_folder,"predicted__blindfamily__program")
    if (combined_prediction["meta"].get("model_sha256")!=source_model_sha or
        [p["operation"] for p in combined_prediction["meta"]["commands"]]!=list(ORDER) or
        [p["operation"] for p in combined_reference["meta"]["commands"]]!=list(ORDER) or
        len(combined_prediction["meta"]["commands"])!=3):
        raise ValueError("Missing original full construction program")
    for p,command in zip(report["learned_construction_program"],
                         combined_prediction["meta"]["commands"]):
        if abs(p["strength"]-command["strength"])>.00001:
            raise ValueError("Combined GLB doesn't contain independently learned strengths")
    compound={op:compare(combined_reference,combined_prediction,op) for op in ORDER}
    # A single GLB must show all three geometry changes together, not just
    # three isolated outputs or a decorative assembly replacement.
    separate_deltas={}
    for op in ORDER:
        field=METRIC[op]
        separate_deltas[op]=round(
            combined_prediction["metrics"][field]-ref_baseline["metrics"][field],6)
    compound_structure=combined_prediction["structural"]
    structural={
        "one_source_native_multi_operation_glb":True,
        "no_nonmanifold_edges":compound_structure["nonmanifold_edges"]==0,
        "no_invalid_triangles":compound_structure["invalid_triangles"]==0,
        "within_mobile_budget":0<compound_structure["triangles"]<=12000,
        "real_recess_depth_in_combined_mesh":separate_deltas["recess_rear_socket"]>.08,
        "real_upper_shoulder_change":separate_deltas["sculpt_cockpit_shoulder"]>.004,
        "real_tapered_nacelle":separate_deltas["loft_rear_nacelle"]>.11,
        "all_single_op_targets_met":all(x["passed"] for x in checks.values()),
        "all_compound_shape_targets_met":all(x["passed"] for x in compound.values())
    }
    return {"schema":SCHEMA,"passed":all(structural.values()),
            "checks":structural,
            "single_operation_reference_errors":checks,
            "combined_shape_reference_errors":compound,
            "compound_measured_deltas":separate_deltas,
            "compound_original_glb_sha256":combined_prediction["sha256"],
            "heldout_reference_glb_sha256":combined_reference["sha256"],
            "owned_model_sha256":source_model_sha,
            "composed_triangle_count":compound_structure["triangles"],
            "original_geometry_generated_by":"AssetWright MiniGeometry/GlbWriter",
            "teacher_supplied_geometry":False,
            "android_default_modified":False,
            "limitations":"Synthetic heldout vehicle family with three known controls, measured geometric proxies; engine housing is a separate part and overall aesthetic quality is not established."}

def run(ref:Path,pred:Path,source:Path,out:Path)->dict:
    answer=audit(ref,pred,source)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(answer,indent=2)+"\n")
    print(json.dumps({"passed":answer["passed"],"checks":answer["checks"],
                      "compound_deltas":answer["compound_measured_deltas"],
                      "shape_errors":answer["combined_shape_reference_errors"],
                      "triangles":answer["composed_triangle_count"]},indent=2))
    if not answer["passed"]:raise SystemExit("Original combined GLB failed geometry acceptance")
    return answer

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--predicted",type=Path,required=True)
    p.add_argument("--learning-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.reference,a.predicted,a.learning_report,a.out)

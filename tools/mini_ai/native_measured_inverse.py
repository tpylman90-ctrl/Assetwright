"""Learn native control strengths from MEASURED original GLB geometry.

The data are source-hashed MeshBuilder/GlbWriter outputs, not external meshes.
A CPU-only monotone response-curve student is fit on coupe + utility
examples. Its inverse predicts strengths for measured targets on a third,
unseen geometric family. A separately validated OWN text classifier chooses
which operation; dependencies are enforced by the native Kotlin interpreter.

This is bounded inverse procedural-parameter estimation, not arbitrary CAD.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

from generated_glb_critic import inspect
from vehicle_design_critic import analyze
from native_socket_audit import points_of
from native_operation_intent_student import OPERATIONS,SCHEMA as OWN_MODEL,infer
from native_operator_proposal_batch import PROOF_PROMPTS

SCHEMA="assetwright-native-measured-geometry-response-v1"
METRIC={
    "recess_rear_socket":"rear_socket_depth_m",
    "sculpt_cockpit_shoulder":"upper_hull_station_halfspan_m",
    "loft_rear_nacelle":"engine_housing_flare_ratio"
}
ORDER=("sculpt_cockpit_shoulder","recess_rear_socket","loft_rear_nacelle")
TRAIN_FAMILIES=("coupe","utility")
UNSEEN="blindfamily"
TRAIN_LEVELS=(.25,.50,.90)
TARGET_LEVELS=(.375,.725)
BOUNDARY_TOL={
    "recess_rear_socket":.035,
    "sculpt_cockpit_shoulder":.035,
    "loft_rear_nacelle":.17,
}

def digest(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def case(folder:Path,name:str)->dict:
    base=folder/name
    meta=json.loads(base.with_suffix(".json").read_text())
    raw=base.with_suffix(".glb").read_bytes()
    if (meta.get("schema")!="assetwright-native-measured-program-v1" or
        meta.get("original_generator")!="android-native-MiniGeometry" or
        meta.get("case")!=name or meta.get("source_glb_sha256")!=digest(raw)):
        raise ValueError("Untrusted original GLB source: "+name)
    phase=meta.get("phase")
    if phase not in ("train","reference","predicted"):
        raise ValueError("Unrecognized source partition")
    geometry=inspect(base.with_suffix(".glb"))
    style=analyze(base.with_suffix(".glb"))
    if geometry["model_sha256"]!=digest(raw) or style["model_sha256"]!=digest(raw):
        raise ValueError("Structural and metric provenance mismatch")
    if geometry["triangles"]>12000 or geometry["nonmanifold_edges"]!=0 or geometry["invalid_triangles"]!=0:
        raise ValueError("Invalid source geometry")
    # Actual native input GLB positions in glTF x/y/up/-z/aft. Only source
    # vertices inside the round 0.17m socket can count as recessed well.
    hull=points_of(base.with_suffix(".glb"))
    stern=min(p[2] for p in hull)
    center_up=.80   # Native controlled benchmark specs keep hullCenterZ=.80
    interior=[p[2]-stern for p in hull if
              .000001 < p[2]-stern < .36 and
              math.hypot(p[0],p[1]-center_up)<.191]
    depth=round(max(interior,default=0.),6)
    # IMPORTANT: the old critic's maximum cockpit span saturated immediately
    # because enabling the operation inserts extra axial stations. Compare
    # homologous VERTICES on the common t=-.05 hull ring instead. The actual
    # ring points exist in both the baseline and the modified native GLB.
    hull_length=max(p[2] for p in hull)-stern
    station=.05*hull_length
    ring=[p for p in hull if abs(p[2]-station)<.001]
    shoulder_candidates=[abs(p[0]) for p in ring if p[1]>.87]
    if len(ring)<12 or len(shoulder_candidates)<4:
        raise ValueError("Missing homologous upper-hull shoulder station")
    station_span=round(max(shoulder_candidates),7)
    values={
        "upper_hull_station_halfspan_m":station_span,
        "rear_socket_depth_m":depth,
        "body_cockpit_shoulder_span":float(
            style["metrics"]["body_cockpit_shoulder_span"]),
        "engine_housing_flare_ratio":float(
            style["metrics"]["engine_housing_flare_ratio"])
    }
    # Never treat this metric proxy as proof of real automotive surfacing.
    return {"name":name,"meta":meta,"metrics":values,
            "sha256":digest(raw),"triangles":geometry["triangles"],
            "structural":geometry}

def validate_response(records:list[dict])->dict:
    rows=defaultdict(lambda:defaultdict(list))
    ids=set()
    for rec in records:
        meta=rec["meta"]
        if meta["phase"]!="train" or meta.get("family") not in TRAIN_FAMILIES:
            raise ValueError("Attempted fitting with heldout or external model")
        identifier=rec["sha256"]
        if identifier in ids:raise ValueError("Repeated original training GLB")
        ids.add(identifier)
        ops=meta.get("commands")
        if not isinstance(ops,list) or len(ops)>1:
            raise ValueError("Compound targets cannot train independent response")
        family=meta["family"]
        if not ops:
            if rec["name"]!="measure__"+family+"__baseline":
                raise ValueError("Unrecognized original baseline")
            rows[family]["baseline"].append(rec)
        else:
            op=ops[0].get("operation")
            strength=ops[0].get("strength")
            if op not in METRIC or type(strength) not in (int,float) or not math.isfinite(strength):
                raise ValueError("Unbounded source native control")
            if not any(abs(strength-lvl)<.00001 for lvl in TRAIN_LEVELS):
                raise ValueError("Training operation level outside declared curriculum")
            rows[family][op].append(rec)
    if set(rows)!=set(TRAIN_FAMILIES):
        raise ValueError("Missing original native training family")
    curves=defaultdict(list)
    for family in TRAIN_FAMILIES:
        if len(rows[family]["baseline"])!=1:raise ValueError("Missing unique baseline")
        base=rows[family]["baseline"][0]
        for op in METRIC:
            samples=rows[family][op]
            if len(samples)!=len(TRAIN_LEVELS):raise ValueError("Missing native control levels")
            measured={}
            for sample in samples:
                level=round(sample["meta"]["commands"][0]["strength"],2)
                if level in measured:raise ValueError("Duplicate source strength")
                metric=METRIC[op]
                response=round(sample["metrics"][metric]-base["metrics"][metric],7)
                measured[level]=response
            if set(measured)!={round(v,2) for v in TRAIN_LEVELS}:
                raise ValueError("Not all training strengths present")
            for strength,response in sorted(measured.items()):
                curves[op].append({"family":family,"strength":strength,
                                   "measured_delta":response})
    result={}
    for op in METRIC:
        grouped=defaultdict(list)
        for row in curves[op]:
            grouped[row["strength"]].append(row["measured_delta"])
        points=[(0.,0.)]
        for level in sorted(grouped):
            points.append((level,sum(grouped[level])/len(grouped[level])))
        # Direction learned from measured geometry, not assumed. Reject
        # discontinuous/nonidentifiable native controls instead of guessing.
        signs=[points[i+1][1]-points[i][1] for i in range(len(points)-1)]
        if not (all(v>1e-5 for v in signs) or all(v< -1e-5 for v in signs)):
            raise ValueError("Cannot invert non-monotonic or unidentifiable geometry response "+op+
                             " measured="+str(points))
        result[op]={"metric":METRIC[op],"curve":points,
                    "families":list(TRAIN_FAMILIES),"slope_direction":
                        "increasing" if signs[0]>0 else "decreasing"}
    return result

def inverse(curve:list[tuple[float,float]],target_delta:float)->float:
    if not math.isfinite(target_delta):raise ValueError("Invalid geometry target")
    pairs=sorted([(float(y),float(x)) for x,y in curve])
    if target_delta<=pairs[0][0]:return round(pairs[0][1],6)
    if target_delta>=pairs[-1][0]:return round(pairs[-1][1],6)
    for (y0,x0),(y1,x1) in zip(pairs,pairs[1:]):
        if y0<=target_delta<=y1:
            return round(x0+(x1-x0)*(target_delta-y0)/(y1-y0),6)
    raise ValueError("Unreachable geometry inverse interval")

def target_delta(target:dict,baseline:dict,op:str)->float:
    if target["meta"]["family"]!=UNSEEN or baseline["meta"]["family"]!=UNSEEN:
        raise ValueError("Heldout geometry family is wrong")
    field=METRIC[op]
    return round(target["metrics"][field]-baseline["metrics"][field],7)

def evaluation(records:list[dict],model:dict,folder:Path,checkpoint:dict)->dict:
    base=case(folder,"measure__blindfamily__baseline")
    if base["meta"]["phase"]!="reference" or base["meta"]["commands"]:
        raise ValueError("Leaked newfamily training baseline")
    details=[]
    for op in ORDER:
        curve=model[op]["curve"]
        for level in TARGET_LEVELS:
            suffix=round(level*1000)
            item=case(folder,"measure__blindfamily__"+op+"__s"+str(suffix))
            if (item["meta"]["phase"]!="reference" or
                len(item["meta"]["commands"])!=1 or
                item["meta"]["commands"][0]["operation"]!=op or
                abs(item["meta"]["commands"][0]["strength"]-level)>.00001):
                raise ValueError("Unverified blind geometry reference")
            measured=target_delta(item,base,op)
            prediction=inverse(curve,measured)
            if not 0<prediction<=1:raise ValueError("Impossible inverse control strength")
            details.append({"operation":op,"metric":METRIC[op],
                            "target_strength":level,"predicted_strength":prediction,
                            "target_delta":measured,
                            "strength_error":round(abs(prediction-level),6),
                            "constant_0_6_error":round(abs(.6-level),6),
                            "original_reference_sha256":item["sha256"]})
    baseline=sum(x["constant_0_6_error"] for x in details)/len(details)
    error=sum(x["strength_error"] for x in details)/len(details)
    if checkpoint.get("schema")!="assetwright-owned-native-operation-intent-student-v1" or checkpoint.get("external_mesh_used") is not False:
        raise ValueError("Untrusted own operation classifier")
    predicted_names=[]
    for prompt in PROOF_PROMPTS:
        prediction=infer(checkpoint,prompt)
        if prediction.get("status")!="native_research_operation_proposal":
            raise ValueError("Original owned classifier did not identify operation")
        predicted_names.append(prediction["operation"])
    if set(predicted_names)!=set(ORDER):
        raise ValueError("OWN classifier failed to identify all modeling operations")
    final=[next(x for x in details if
                x["operation"]==op and abs(x["target_strength"]-.725)<.000001)
           for op in ORDER]
    # Classifier predicts the operation names, geometry inverse predicts the
    # control strength; sorting only enforces real native dependencies.
    plan=[{"operation":op,"strength":item["predicted_strength"]}
          for op,item in zip(ORDER,final)]
    return {"schema":SCHEMA,"research_status":"verified_inverse_geometry_response" if
            error<.12 and error<baseline-.025 else "rejected_inverse_geometry_response",
            "train_family_count":len(TRAIN_FAMILIES),
            "train_source_glb_count":len(records),
            "new_blind_family":UNSEEN,"new_blind_strength_levels":list(TARGET_LEVELS),
            "exact_blind_geometry_errors":details,
            "mean_strength_absolute_error":round(error,6),
            "constant_strength_mean_error":round(baseline,6),
            "student_classifier_selected_operations":predicted_names,
            "learned_construction_program":plan,
            "source_checkpoint_sha256":checkpoint["_source_sha256"],
            "externally_generated_geometry_used":False,
            "training_saw_heldout_geometry":False,
            "no_automatic_android_promotion":True,
            "limitations":"Source GLBs are synthetic original vehicle meshes; measured inverse on third parameterized hover vehicle only, not novel real asset or artistic visual quality."}

def train_and_propose(source:Path,checkpoint_file:Path,out:Path)->dict:
    training=[]
    for family in TRAIN_FAMILIES:
        training.append(case(source,"measure__"+family+"__baseline"))
        for op in ORDER:
            for level in TRAIN_LEVELS:
                training.append(case(source,"measure__"+family+"__"+op+
                                     "__s"+str(round(level*1000))))
    model=validate_response(training)
    sha=digest("|".join(sorted(x["sha256"] for x in training)).encode())
    raw=checkpoint_file.read_bytes()
    checkpoint=json.loads(raw)
    checkpoint["_source_sha256"]=digest(raw)
    report=evaluation(training,model,source,checkpoint)
    report["training_glb_hashes_sha256"]=sha
    report["response_curves"]=model
    out.mkdir(parents=True,exist_ok=True)
    (out/"inverse_report.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"learned_response_curves.json").write_text(json.dumps({
        "schema":SCHEMA,"response_curves":model,"source_hash":sha,
        "source_checkpoint_sha256":checkpoint["_source_sha256"],
        "input_training_families":list(TRAIN_FAMILIES),
        "training_uses_reference_family":False},indent=2)+"\n")
    (out/"program.properties").unlink(missing_ok=True)
    if report["research_status"]=="verified_inverse_geometry_response":
        plan=report["learned_construction_program"]
        lines=["schema=assetwright-native-measured-inverse-plan-v1",
               "source_model_sha256="+checkpoint["_source_sha256"],
               "geometry_training_sha256="+sha,
               "provenance=OWN-classifier-and-native-GLB-measurements",
               "count=3"]
        for i,p in enumerate(plan):
            lines += ["step"+str(i)+".operation="+p["operation"],
                      "step"+str(i)+".strength="+str(p["strength"])]
        (out/"program.properties").write_text("\n".join(lines)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in (
        "exact_blind_geometry_errors","response_curves")},indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=train_and_propose(a.source,a.checkpoint,a.out)
    if result["research_status"]!="verified_inverse_geometry_response":
        raise SystemExit("Inverse geometry model failed its declared unseen-family gate")

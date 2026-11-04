"""Source-grounded native composition student, six controls / three active ops.

All 1120 GLBs are created by OWN Kotlin NativeCompositionLab; this module
reads only their physical vertices as inputs. Program labels/strengths are
supervision and metadata for provenance, never model input features.
This experiment is synthetic compositional learning, NOT CAD generalization.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import numpy as np

from generated_glb_critic import _accessor, _read_glb, inspect

SCHEMA="assetwright-native-composition-v1"
MODEL="assetwright-owned-native-composition-linear-v1"
ORDER=("SECTION_LOFT","RIBBED_FAIRING","SUPERELLIPSE_PROFILE",
       "LOWER_RECESS","SECTION_TWIST","TANGENT_SWEEP")
PAIRS=[(a,b,c) for a in range(6) for b in range(a+1,6)
       for c in range(b+1,6)]
PARTITIONS={
    "train":tuple(f"ctrain{i:02d}" for i in range(1,11)),
    "validation":tuple(f"cval{i}" for i in range(1,5)),
    "aspect_shift":tuple(f"cshift{i}" for i in range(1,5))
}
SLOTS={"train":4,"validation":2,"aspect_shift":2}
TOTAL=1120
N=32
M=32

def feature_vector(path:Path,dims:tuple[float,float,float])->tuple[np.ndarray,dict]:
    doc,blob,sha=_read_glb(path)
    meshes=doc.get("meshes",[])
    if len(meshes)!=1 or len(meshes[0].get("primitives",[]))!=1:
        raise ValueError("Expected a single connected original hull")
    primitive=meshes[0]["primitives"][0]
    points=np.asarray(
        _accessor(doc,blob,primitive["attributes"]["POSITION"],"positions"),
        dtype=np.float64)
    if points.shape != ((M+1)*N+2,3):
        raise ValueError("Wrong native corresponding section count")
    rings=points[:(M+1)*N].reshape((M+1,N,3))
    # glTF axes: (source X, source Z, -source longitudinal Y)
    center=(rings[:,0,:]+rings[:,16,:])*.5
    offsets=rings-center[:,None,:]
    radius0=np.linalg.norm(offsets[:,0,:],axis=1)
    radius8=np.linalg.norm(offsets[:,8,:],axis=1)
    if np.min(radius0)<.05 or np.min(radius8)<.05:
        raise ValueError("Invalid native cross section")
    length,width,height=dims
    if np.max(np.abs(center[:,2]-
          np.linspace(length/2,-length/2,M+1)))>.25:
        raise ValueError("Untrustworthy source section centerline")
    u=np.arange(M+1)/M
    w=radius0/(width*.5)
    h=radius8/(height*.5)
    sweep_max=min(width*.20,length*.08)
    centerline=center[:,0]/max(sweep_max,.02)
    # Orientation-aware geometry measurements: radial lengths in full 3D
    # remain invariant to both local twist and moving sweep frame.
    phi=np.arctan2(offsets[:,0,1],offsets[:,0,0])
    # Swirl at u=1 and u=.5: projected world-angle sensor; the trained
    # model must compensate for swept-frame foreshortening across aspects.
    twist_proxy=np.array([phi[16],phi[24],phi[32]])/(math.pi*.47)
    numerator=np.linalg.norm(offsets[:,4,:],axis=1)
    rounded=numerator/np.maximum(
        np.sqrt(.5*(radius0**2+radius8**2)),.001)-1
    # Upper/lower diagonal asymmetry = actual same-source hull recess.
    diag_up=(offsets[:,4,:]**2).sum(axis=1)
    diag_down=(offsets[:,28,:]**2).sum(axis=1)
    recess=(diag_up-diag_down)/(radius0**2)
    # Distinct longitudinal profile probes. The original six operations
    # have different physical response frequencies; not one filename bit
    # is supplied to the learner.
    stations=[0,3,4,5,6,7,8,9,10,11,12,14,16,18,20,22,24,26,28,30,32]
    controls=[
        *[w[i]-1 for i in stations],
        *[h[i]-1 for i in (0,6,12,16,18,24,28,32)],
        *[centerline[i] for i in (4,8,12,16,20,24,28)],
        *list(twist_proxy),
        *[rounded[i] for i in (0,8,16,24,32)],
        *[recess[i] for i in (8,12,16,20,24)],
        # Local finite-difference curvature proxy, not G2 continuity.
        *[w[i+1]-2*w[i]+w[i-1] for i in (5,7,9,12,16,19,23,27)]
    ]
    result=np.asarray(controls,dtype=np.float64)
    if not np.all(np.isfinite(result)) or np.max(np.abs(result))>6.:
        raise ValueError("Nonphysical normalized source morphology")
    curvature=np.max(np.abs(np.diff(w,n=2)))
    if curvature>.11:
        raise ValueError("Sharp longitudinal width discontinuity in source")
    return result,{"max_station_width_second_difference":float(curvature),
                   "source_glb_sha256":sha}


def expected_stems()->set[str]:
    return {f"{phase}__{family}__p{plan:02d}__v{slot}"
            for phase,families in PARTITIONS.items()
            for family in families
            for plan in range(20)
            for slot in range(SLOTS[phase])}


def read_case(source:Path,stem:str)->dict:
    path=source/(stem+".glb")
    meta=json.loads((source/(stem+".json")).read_text())
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    match=re.fullmatch(
        r"(train|validation|aspect_shift)__(ctrain\d\d|cval\d|cshift\d)__p(\d\d)__v(\d)",
        stem)
    if match is None:
        raise ValueError("Unapproved native program identity")
    phase,family,plan_str,slot_str=match.groups()
    plan,slot=int(plan_str),int(slot_str)
    if not (family in PARTITIONS[phase] and plan in range(20)
            and slot in range(SLOTS[phase])):
        raise ValueError("Unknown program/family/phase")
    dims=tuple(meta.get(x) for x in ("length","width","height"))
    commands=meta.get("commands")
    if not (
        meta.get("schema")==SCHEMA and meta.get("case")==stem
        and meta.get("phase")==phase and meta.get("family")==family
        and meta.get("plan_index")==plan
        and meta.get("generator")=="AssetWright-NativeCompositionLab"
        and meta.get("source_glb_sha256")==sha
        and meta.get("stations")==32 and meta.get("segments")==32
        and all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in dims)
        and isinstance(commands,list) and len(commands)==3):
        raise ValueError("Untrusted original source or metadata")
    expected_ops=[ORDER[i] for i in PAIRS[plan]]
    if [command.get("operation") for command in commands]!=expected_ops:
        raise ValueError("Operation ordering or labels corrupted")
    expected_strengths=[]
    for step,command in enumerate(commands):
        value=command.get("strength")
        if type(value) not in (float,int) or not math.isfinite(value):
            raise ValueError("Nonfinite source strength")
        family_index=PARTITIONS[phase].index(family)
        if phase=="train":
            target=(17+((family_index*31+plan*23+slot*13+step*19)%68))/100
        elif phase=="validation":
            target=(18+((family_index*29+plan*17+slot*23+step*11)%66))/100+.005
        else:
            target=(19+((family_index*19+plan*29+slot*17+step*23)%65))/100+.007
        if abs(value-target)>2e-5:
            raise ValueError("Incorrect native control provenance")
        expected_strengths.append(float(value))
    topology=inspect(path)
    if not (
        topology["model_sha256"]==sha and topology["mesh_parts"]==1
        and topology["triangles"]==M*N*2+N*2
        and topology["invalid_triangles"]==0
        and topology["nonmanifold_edges"]==0
        and topology["boundary_edges"]==0
        and topology["inverted_closed_parts"]==0
        and topology["parts"][0]["signed_volume"]>0):
        raise ValueError("Invalid actual one-shell native geometry")
    inputs,physics=feature_vector(path,dims)
    target=np.zeros(6)
    for op,val in zip(expected_ops,expected_strengths):
        target[ORDER.index(op)]=val
    return {"stem":stem,"phase":phase,"family":family,"plan":plan,
            "source_sha256":sha,"dimensions":dims,
            "features":inputs,"targets":target,"physics":physics}


def load_dataset(source:Path)->list[dict]:
    stems=expected_stems()
    if len(stems)!=TOTAL:
        raise ValueError("Incorrect expected composition batch")
    found={x.stem for x in source.glob("*.glb")}
    manifests={x.stem for x in source.glob("*.json")}
    if stems!=found or stems!=manifests:
        raise ValueError("Incomplete or extraneous original GLB source set")
    rows=[read_case(source,s) for s in sorted(stems)]
    if len({r["source_sha256"] for r in rows})!=TOTAL:
        raise ValueError("Repeated GLB sources, even with different labels")
    for phase,families in PARTITIONS.items():
        actual={r["family"] for r in rows if r["phase"]==phase}
        if actual!=set(families):
            raise ValueError("Split family mismatch")
    return rows


def design(X:np.ndarray)->np.ndarray:
    # Ridge student includes measured interaction features: a very small
    # second-order native regression, not a lookup by source program/filename.
    X=np.asarray(X)
    m=X.shape[1]
    scale=np.std(X,axis=0)
    mean=np.mean(X,axis=0)
    return X,mean,np.maximum(scale,.03)


def fit_student(train:list[dict])->dict:
    if len(train)!=800 or any(row["phase"]!="train" for row in train):
        raise ValueError("Exactly 800 native training compositions required")
    plans=Counter(row["plan"] for row in train)
    if len(plans)!=20 or any(v!=40 for v in plans.values()):
        raise ValueError("Missing composition-plan balance")
    X=np.stack([r["features"] for r in train])
    Y=np.stack([r["targets"] for r in train])
    _,mean,std=design(X)
    A=(X-mean)/std
    # Quadratic cross terms are necessary for independent twist+rounding
    # and loft+ribs composition, but do not use ground truth plan labels
    # during actual inference.
    primary=A[:,::4]
    polynomial=primary[:,:,None]*primary[:,None,:]
    tri=np.triu_indices(primary.shape[1])
    poly=polynomial[:,tri[0],tri[1]]
    features=np.column_stack((np.ones(len(train)),A,poly))
    lam=.075
    normal=features.T@features+lam*np.eye(features.shape[1])
    normal[0,0]-=lam
    weights=np.linalg.solve(normal,features.T@Y)
    return {"schema":MODEL,"operations":list(ORDER),"training_sources":800,
            "feature_mean":mean.tolist(),"feature_std":std.tolist(),
            "weights":weights.tolist(),
            "polynomial_step":4,
            "regularization":lam,
            "model_type":"owned_quadratic_ridge_inverse_program",
            "source_hashes_sha256":hashlib.sha256(
                "\n".join(sorted(r["source_sha256"] for r in train)).encode()).hexdigest(),
            "android_deployable":False,
            "external_generator":False}


def predict(model:dict,features:np.ndarray)->tuple[np.ndarray,np.ndarray]:
    values=np.atleast_2d(features)
    mean=np.array(model["feature_mean"])
    std=np.array(model["feature_std"])
    z=(values-mean)/std
    primary=z[:,::model["polynomial_step"]]
    gram=primary[:,:,None]*primary[:,None,:]
    tri=np.triu_indices(primary.shape[1])
    X=np.column_stack((np.ones(len(values)),z,gram[:,tri[0],tri[1]]))
    strengths=np.clip(X@np.asarray(model["weights"]),0,1)
    selected=np.argsort(-strengths,axis=1)[:,:3]
    predicted=np.zeros_like(strengths)
    np.put_along_axis(predicted,selected,
                       np.take_along_axis(strengths,selected,axis=1),axis=1)
    return predicted,selected


def evaluate(model:dict,rows:list[dict],phase:str)->tuple[dict,list[dict]]:
    if not rows or any(r["phase"]!=phase for r in rows):
        raise ValueError("Cross-partition validation leak")
    X=np.stack([r["features"] for r in rows])
    predicted,selected=predict(model,X)
    target=np.stack([r["targets"] for r in rows])
    truth=target>0
    actual=predicted>0
    plan_match=np.all(actual==truth,axis=1)
    mae=np.mean(np.abs(predicted-target),axis=1)
    oracle_mae=np.sum(
        np.abs(predicted-target)*truth,axis=1)/3
    baseline=np.full_like(target,0.)
    baseline[truth]=.5
    baseline_mae=np.sum(np.abs(baseline-target),axis=1)/3
    per_op={}
    for idx,name in enumerate(ORDER):
        tp=int(np.sum(actual[:,idx]&truth[:,idx]))
        fp=int(np.sum(actual[:,idx]&~truth[:,idx]))
        fn=int(np.sum(~actual[:,idx]&truth[:,idx]))
        per_op[name]={"precision":tp/max(1,tp+fp),
                     "recall":tp/max(1,tp+fn),
                     "true_positive":tp,"false_positive":fp,
                     "false_negative":fn}
    cases=[]
    for r,p,matching,err in zip(rows,predicted,plan_match,oracle_mae):
        cases.append({
            "stem":r["stem"],"source_sha256":r["source_sha256"],
            "true_controls":r["targets"].tolist(),
            "estimated_controls":p.tolist(),
            "plan_exact":bool(matching),
            "active_strength_mae":float(err)
        })
    summary={
        "phase":phase,"sources":len(rows),
        "exact_three_operation_plan_accuracy":float(np.mean(plan_match)),
        "all_six_control_mae":float(np.mean(mae)),
        "active_strength_mae":float(np.mean(oracle_mae)),
        "constant_point_five_active_baseline_mae":float(np.mean(baseline_mae)),
        "per_operation":per_op,
        "worst_case_active_strength_mae":float(max(oracle_mae))
    }
    return summary,cases


def acceptance(validation:dict,shift:dict)->dict:
    return {
        "heldout_exact_program_accuracy":validation[
            "exact_three_operation_plan_accuracy"]>=.93,
        "aspect_exact_program_accuracy":shift[
            "exact_three_operation_plan_accuracy"]>=.86,
        "heldout_active_strength_mae":validation["active_strength_mae"]<=.065,
        "aspect_active_strength_mae":shift["active_strength_mae"]<=.095,
        "heldout_per_operation_recall":all(
            x["recall"]>=.9 for x in validation["per_operation"].values()),
        "aspect_per_operation_recall":all(
            x["recall"]>=.8 for x in shift["per_operation"].values()),
        "beats_constant_baseline_heldout":(
            validation["constant_point_five_active_baseline_mae"]-
            validation["active_strength_mae"]>=.12),
        "beats_constant_baseline_aspect":(
            shift["constant_point_five_active_baseline_mae"]-
            shift["active_strength_mae"]>=.09),
    }


def run(source:Path,out:Path)->dict:
    rows=load_dataset(source)
    train=[r for r in rows if r["phase"]=="train"]
    val=[r for r in rows if r["phase"]=="validation"]
    shift=[r for r in rows if r["phase"]=="aspect_shift"]
    if (len(train),len(val),len(shift))!=(800,160,160):
        raise ValueError("Unexpected program learning split")
    model=fit_student(train)
    val_metrics,val_cases=evaluate(model,val,"validation")
    shift_metrics,shift_cases=evaluate(model,shift,"aspect_shift")
    gates=acceptance(val_metrics,shift_metrics)
    passed=all(gates.values())
    report={
        "schema":"assetwright-native-three-operation-composition-study-v1",
        "status":"passed_development_study" if passed else "rejected_development_study",
        "original_source_glbs":TOTAL,"native_training_glbs":800,
        "dimension_holdout_glbs":160,"aspect_holdout_glbs":160,
        "unique_source_glbs":TOTAL,
        "operation_vocabulary":list(ORDER),
        "program_options":20,"active_operations_per_program":3,
        "single_source_connected_hull":True,"max_triangles":M*N*2+2*N,
        "dimension_holdout":val_metrics,"aspect_holdout":shift_metrics,
        "checks":gates,
        "training_hash_digest":model["source_hashes_sha256"],
        "heldout_source_hashes":sorted(r["source_sha256"] for r in val),
        "aspect_source_hashes":sorted(r["source_sha256"] for r in shift),
        "limitations":"All shapes from one original Kotlin generator; this is a constrained 3-of-6 dependency-ordered program learner, not general text-to-CAD, Boolean openings, G2 surfacing, or unseen asset categories.",
        "android_deployed":False,"prior_checkpoints_unchanged":True,
        "human_visual_approval":False
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"composition_report.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"candidate_composition_student.json").write_text(json.dumps(model,indent=2)+"\n")
    (out/"heldout_predictions.json").write_text(json.dumps(
        {"validation":val_cases,"aspect_shift":shift_cases},indent=2)+"\n")
    with (out/"inverse_programs.tsv").open("w") as stream:
        for original,case in zip([*val,*shift],[*val_cases,*shift_cases]):
            assert original["stem"]==case["stem"]
            chosen=[ORDER[i] for i in range(6)
                    if case["estimated_controls"][i]>0]
            weights=[case["estimated_controls"][ORDER.index(x)] for x in chosen]
            stream.write("\t".join((original["stem"],
                ",".join(chosen),",".join(f"{x:.8f}" for x in weights),
                ",".join(str(x) for x in original["dimensions"])))+"\n")
    print(json.dumps({
        "status":report["status"],"checks":gates,
        "heldout_exact_program_accuracy":val_metrics["exact_three_operation_plan_accuracy"],
        "aspect_exact_program_accuracy":shift_metrics["exact_three_operation_plan_accuracy"],
        "heldout_strength_mae":val_metrics["active_strength_mae"],
        "aspect_strength_mae":shift_metrics["active_strength_mae"],
    },indent=2))
    if not passed:
        raise SystemExit("Native composed program student rejected under fixed gates")
    return report


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    a=cli.parse_args()
    run(a.source,a.out)

"""Original supervised CAD-surface student, never an STL/STEP generator.

Inference inputs: whitelisted operation sequence and safe numeric code
literals. TRAINING labels: independently measured licensed STL geometry.
Official validation labels are never fit, used to select ridge strength,
or added to the model input.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from cad_surface_teacher import GEOMETRY_SCHEMA,TARGETS
from cad_shape_school import complexity_features

MODEL="assetwright-owned-cad-surface-signature-v1"
REPORT="assetwright-cad-stl-surface-transfer-study-v1"

def verify(train:dict,valid:dict)->tuple[list[dict],list[dict]]:
    if any(x.get("schema")!=GEOMETRY_SCHEMA for x in (train,valid)):
        raise ValueError("Unsupported real-geometry teacher")
    if (train.get("official_split"),valid.get("official_split"))!=("train","validation"):
        raise ValueError("Source split contamination")
    if train.get("dataset_revision")!=valid.get("dataset_revision") or \
       len(str(train.get("dataset_revision","")))!=40:
        raise ValueError("Upstream source revision mismatch")
    if train.get("license")!="Apache-2.0" or valid.get("license")!="Apache-2.0":
        raise ValueError("Missing source mesh training license")
    if train.get("source_offset",0)<2200 or valid.get("source_offset",0)<1500:
        raise ValueError("Previously exposed CAD examples must not be reused")
    if any(x.get("downloaded_scripts_executed") is not False or
           x.get("downloaded_meshes_exported_as_native") is not False or
           x.get("mesh_bytes_retained") is not False for x in (train,valid)):
        raise ValueError("External geometry boundary violated")
    a=train.get("records",[])
    b=valid.get("records",[])
    if len(a)<256 or len(b)<64:
        raise ValueError("Insufficient actual STL surface measurements")
    for doc,rows in ((train,a),(valid,b)):
        ids=set();scripts=set();meshes=set()
        for r in rows:
            if r.get("split")!=doc["official_split"]:
                raise ValueError("Mixed official source splits")
            sid=r.get("source_id");code=r.get("code_sha256");mesh=r.get("stl_sha256")
            if not (isinstance(sid,str) and isinstance(code,str) and
                    isinstance(mesh,str) and len(code)==64 and len(mesh)==64):
                raise ValueError("Missing verified source evidence")
            if sid in ids or code in scripts or mesh in meshes:
                raise ValueError("Repeated geometry or code in source split")
            ids.add(sid);scripts.add(code);meshes.add(mesh)
            y=r.get("surface_target")
            x=r.get("safe_numeric_cad_features")
            if (not isinstance(y,list) or len(y)!=len(TARGETS) or
                not isinstance(x,list) or len(x)!=18 or
                any(type(v) not in (int,float) or not math.isfinite(v)
                    for v in (*x,*y)) or
                any(v<0 or v>4 for v in y) or
                any(v<-.999999 or v>1.000001 for v in x)):
                raise ValueError("Invalid independently measured geometry vector")
            if not isinstance(r.get("operations"),list) or len(r["operations"])<3:
                raise ValueError("Untrusted source program")
    if (({r["source_id"] for r in a}&{r["source_id"] for r in b}) or
        ({r["code_sha256"] for r in a}&{r["code_sha256"] for r in b}) or
        ({r["stl_sha256"] for r in a}&{r["stl_sha256"] for r in b})):
        raise ValueError("CAD source hash collision between train and holdout")
    return a,b

def features(row:dict,include_literals:bool)->np.ndarray:
    ops=complexity_features(row)
    literals=row["safe_numeric_cad_features"] if include_literals else []
    # No STL vertex, source dimensions, target surface ratio, face count,
    # target hash, UUID, split or future answer goes into the predictor.
    return np.asarray([*ops,*literals],dtype=np.float64)

def model_fit(rows:list[dict],ridge:float,include_literals:bool)->dict:
    x=np.stack([features(row,include_literals) for row in rows])
    y=np.stack([row["surface_target"] for row in rows])
    mean=x.mean(axis=0)
    std=np.maximum(x.std(axis=0),.08)
    scaled=(x-mean)/std
    x_matrix=np.column_stack((np.ones(len(rows)),scaled))
    # Work on a normalized target to avoid concentrating only on one
    # large-magnitude surface ratio. Fixed min target standard deviation.
    target_mean=y.mean(axis=0)
    target_std=np.maximum(y.std(axis=0),.08)
    normalized=(y-target_mean)/target_std
    penalty=np.eye(x_matrix.shape[1])*ridge
    penalty[0,0]=0
    weight=np.linalg.solve(x_matrix.T@x_matrix+penalty,
                           x_matrix.T@normalized)
    return {"ridge":ridge,"include_literals":include_literals,
            "input_mean":mean.tolist(),"input_std":std.tolist(),
            "target_mean":target_mean.tolist(),"target_std":target_std.tolist(),
            "coefficients":weight.tolist()}

def predict(model:dict,rows:list[dict])->np.ndarray:
    x=np.stack([features(row,model["include_literals"]) for row in rows])
    x=(x-np.asarray(model["input_mean"]))/np.asarray(model["input_std"])
    x=np.column_stack((np.ones(len(x)),x))
    prediction=x@np.asarray(model["coefficients"])
    prediction=prediction*np.asarray(model["target_std"])+np.asarray(model["target_mean"])
    upper=np.asarray([1,1,4,1,1])
    return np.maximum(0.,np.minimum(prediction,upper))

def score(pred:np.ndarray,rows:list[dict])->dict:
    actual=np.stack([row["surface_target"] for row in rows])
    # Important: no all-positive "accuracy" for continuous shape. Report
    # MAE per physically meaningful target and aggregate scale-adjusted MAE.
    err=np.abs(pred-actual)
    scaled=err/np.asarray([1.,1.,4.,1.,1.])
    return {
        "sources":len(rows),
        "scaled_surface_signature_mae":float(scaled.mean()),
        "per_target_mae":{key:float(err[:,i].mean()) for i,key in enumerate(TARGETS)},
        "per_target_scaled_mae":{key:float(scaled[:,i].mean())
                                  for i,key in enumerate(TARGETS)}
    }

def split_internal(rows:list[dict]):
    # Hash-defined split from original source code, not a sampled subset of
    # official unseen validation and not an old exposed benchmark.
    fit=[row for row in rows
         if int(row["code_sha256"][:8],16)%5!=0]
    develop=[row for row in rows
             if int(row["code_sha256"][:8],16)%5==0]
    if len(fit)<200 or len(develop)<35:
        raise ValueError("Insufficient internal modeling/development source split")
    return fit,develop

def run(train_file:Path,validation_file:Path,out:Path)->dict:
    train_doc=json.loads(train_file.read_text())
    val_doc=json.loads(validation_file.read_text())
    train,holdout=verify(train_doc,val_doc)
    fitted,development=split_internal(train)
    # All model selection, including choice of regularization, happens
    # strictly on an INTERNAL development cohort.
    candidates=[]
    for use_literals in (False,True):
        for ridge in (1.,10.,40.):
            candidate=model_fit(fitted,ridge,use_literals)
            result=score(predict(candidate,development),development)
            candidates.append((result["scaled_surface_signature_mae"],
                               use_literals,ridge))
    selection={}
    for use_literals in (False,True):
        selected=min(c for c in candidates if c[1]==use_literals)
        selection[use_literals]=selected[2]
    ops_model=model_fit(fitted,selection[False],False)
    shape_model=model_fit(fitted,selection[True],True)
    # One untouched official validation score, no selection on this cohort.
    ops=score(predict(ops_model,holdout),holdout)
    owned=score(predict(shape_model,holdout),holdout)
    target_median=np.median(np.stack([r["surface_target"] for r in fitted]),axis=0)
    prior=score(np.tile(target_median,(len(holdout),1)),holdout)
    improvement_vs_median=1-owned["scaled_surface_signature_mae"]/prior[
        "scaled_surface_signature_mae"]
    improvement_vs_operations=1-owned["scaled_surface_signature_mae"]/ops[
        "scaled_surface_signature_mae"]
    target_gains=sum(owned["per_target_scaled_mae"][k]<
                    prior["per_target_scaled_mae"][k] for k in TARGETS)
    checks={
        "licensed_disjoint_real_STL_sources":True,
        "source_train_at_least_256":len(train)>=256,
        "source_validation_at_least_64":len(holdout)>=64,
        "improvement_vs_train_only_median":improvement_vs_median>=.05,
        "new_numeric_geometry_beats_operations_only":improvement_vs_operations>=.015,
        "at_least_three_surface_targets_better_than_median":target_gains>=3,
        "max_scaled_surface_signature_mae":owned["scaled_surface_signature_mae"]<=.18
    }
    accepted=all(checks.values())
    report={
        "schema":REPORT,
        "status":"validated_research_surface_teacher" if accepted else "rejected_inconclusive",
        "licensed_dataset":train_doc["dataset"],"license":train_doc["license"],
        "dataset_revision":train_doc["dataset_revision"],
        "train_source_count":len(train),"official_fresh_validation_sources":len(holdout),
        "internal_fit_sources":len(fitted),"internal_development_sources":len(development),
        "train_offset":train_doc["source_offset"],
        "validation_offset":val_doc["source_offset"],
        "surface_target_names":list(TARGETS),
        "source_meshes_are_numerical_teachers_only":True,
        "teacher_method":"bounded binary STL triangle geometry, welded measurement-only adjacency",
        "baseline_train_median":prior,"operations_only_baseline":ops,
        "owned_literals_and_ops_student":owned,
        "relative_gain_vs_median":improvement_vs_median,
        "relative_gain_vs_operations_only":improvement_vs_operations,
        "improved_target_count_vs_median":target_gains,
        "internal_development_selection":[
            {"include_literals":b,"ridge":r,"scaled_mae":e}
            for e,b,r in sorted(candidates)
        ],
        "precommitted_checks":checks,
        "actually_generated_native_GLBS":0,
        "CAD_code_executed":False,"outside_STL_imported_into_android":False,
        "student_deployed":False,"human_approved":False,
        "limitations":"Surface geometry descriptors, NOT reconstructed geometry, real fillet radius, G2 continuity, verified booleans, 3D production modeling, or design intent."
    }
    model={
        "schema":MODEL,"scope":"research_only",
        "source":"ADSKAILab/Zero-To-CAD-100k",
        "source_revision":train_doc["dataset_revision"],
        "source_stl_target_names":list(TARGETS),
        "train_hash_digest":hashlib.sha256("\n".join(sorted(
            r["stl_sha256"] for r in train)).encode()).hexdigest(),
        "ops_only_baseline":ops_model,
        "owned_numeric_surface_student":shape_model,
        "selected_from_internal_development_only":True,
        "validated_on_official_unseen":accepted,
        "allowed_for_native_geometry":False,
        "outside_mesh_generator":False,"android_deployable":False
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"candidate_surface_student.json").write_text(json.dumps(model,indent=2)+"\n")
    (out/"source_hash_manifest.json").write_text(json.dumps({
        "dataset_revision":train_doc["dataset_revision"],
        "train":[{"source_id":r["source_id"],"code_sha256":r["code_sha256"],
                  "stl_sha256":r["stl_sha256"]} for r in train],
        "validation":[{"source_id":r["source_id"],"code_sha256":r["code_sha256"],
                       "stl_sha256":r["stl_sha256"]} for r in holdout]
    },indent=2)+"\n")
    print(json.dumps({"status":report["status"],
        "train":len(train),"validation":len(holdout),
        "median":prior["scaled_surface_signature_mae"],
        "operations":ops["scaled_surface_signature_mae"],
        "student":owned["scaled_surface_signature_mae"],
        "checks":checks
    },indent=2))
    if not accepted:
        raise SystemExit("Surface-descriptor student REJECTED under original thresholds")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train",type=Path,required=True)
    p.add_argument("--validation",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.train,a.validation,a.out)

if __name__=="__main__":main()

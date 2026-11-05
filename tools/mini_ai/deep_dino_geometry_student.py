"""Safe CAD-parameter + frozen DINO teaching for AssetWright's OWN student.

Select a simple or nonlinear geometry-aware visual student using INTERNAL
source-hash development examples only. Score a fresh official validation split
once. Never use DINOv2 or third-party geometry at inference or in Android.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from deep_dino_curriculum import NUMERIC_DIM, NUMERIC_SCHEMA
from deep_dino_student import check_splits, split_for_development, validated_rows
from zero_to_cad_visual_student import DIM as OPS_DIM

MODEL="assetwright-owned-geometry-aware-dino-student-v2"
OUT=24
HIDDEN=48


def geometry_rows(manifest:dict,teacher:dict,split:str)->list[dict]:
    if manifest.get("numeric_feature_schema")!=NUMERIC_SCHEMA:
        raise ValueError("Missing audited CAD literal geometry schema")
    rows=validated_rows(manifest,teacher,split)
    source={item["source_id"]:item for item in manifest["records"]}
    for row in rows:
        values=source[row["source_id"]].get("numeric_cad_features")
        if not isinstance(values,list) or len(values)!=NUMERIC_DIM or any(
            type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1.000001
            for v in values
        ):
            raise ValueError("Unverified bounded source CAD geometry dimensions")
        row["x"]+=list(values)
        row["literal_geometry_evidence"]=any(abs(v)>1.e-10 for v in values)
    return rows


def fit(train_doc:dict, train_teacher:dict,
        valid_doc:dict,valid_teacher:dict)->tuple[dict,dict]:
    if (train_doc.get("dataset_revision")!=valid_doc.get("dataset_revision")
        or train_doc.get("dataset")!=valid_doc.get("dataset")):
        raise ValueError("Mismatched pinned source versions")
    train=geometry_rows(train_doc,train_teacher,"train")
    validation=geometry_rows(valid_doc,valid_teacher,"validation")
    check_splits(train,validation)
    fitted,development=split_for_development(train)

    import numpy as np
    def arrays(rows):
        return (np.asarray([r["x"] for r in rows],dtype=np.float64),
                np.asarray([r["y"] for r in rows],dtype=np.float64))
    x,y=arrays(fitted)
    xd,yd=arrays(development)
    xv,yv=arrays(validation)
    input_dim=OPS_DIM+NUMERIC_DIM
    if x.shape[1]!=input_dim or y.shape[1]!=OUT:
        raise ValueError("Unexpected geometry-aware owned student dimension")
    coverage=sum(r["literal_geometry_evidence"] for r in fitted)/len(fitted)
    if coverage < .50:
        raise ValueError("Not enough safe source numeric geometry evidence")

    def ridge_fit(a,b,reg):
        padded=np.column_stack((a,np.ones(len(a))))
        penalty=np.eye(padded.shape[1])*reg
        penalty[-1,-1]=0.0
        return np.linalg.solve(padded.T@padded+penalty,padded.T@b)
    def line_predict(a,w):
        return np.column_stack((a,np.ones(len(a))))@w
    error=lambda a,b:float(np.mean((a-b)**2))

    # Fit only on development-training sources. Internal development selects
    # the regularization and model family; official validation never does.
    ops_candidates=[]
    for lam in (0.5,2.0,8.0):
        w=ridge_fit(x[:,:OPS_DIM],y,lam)
        ops_candidates.append((error(line_predict(xd[:,:OPS_DIM],w),yd),lam,w))
    _,ops_reg,operations_only=min(ops_candidates,key=lambda p:p[0])

    full_candidates=[]
    for lam in (0.5,2.0,8.0):
        w=ridge_fit(x,y,lam)
        full_candidates.append((error(line_predict(xd,w),yd),lam,w))
    best_linear_dev,full_reg,full_ridge=min(full_candidates,key=lambda p:p[0])
    best_dev=best_linear_dev
    selected="safe_geometry_ridge"
    chosen_residual=None

    # The nonlinear candidate is a residual over the already trained native
    # numeric CAD prior. It must demonstrate DEVELOPMENT improvement to win.
    rng=np.random.default_rng(2741)
    weights={"w1":rng.normal(0,.05,(input_dim,HIDDEN)),
             "b1":np.zeros(HIDDEN),
             "w2":rng.normal(0,.005,(HIDDEN,OUT)),
             "b2":np.zeros(OUT)}
    moment={k:np.zeros_like(v) for k,v in weights.items()}
    variance={k:np.zeros_like(v) for k,v in weights.items()}
    t=0
    base_train=line_predict(x,full_ridge)
    base_dev=line_predict(xd,full_ridge)
    for epoch in range(200):
        hidden=np.tanh(x@weights["w1"]+weights["b1"])
        pred=base_train+hidden@weights["w2"]+weights["b2"]
        d=2*(pred-y)/(len(x)*OUT)
        grads={}
        grads["w2"]=hidden.T@d+.0005*weights["w2"]
        grads["b2"]=d.sum(axis=0)
        d_hidden=(d@weights["w2"].T)*(1-hidden**2)
        grads["w1"]=x.T@d_hidden+.0005*weights["w1"]
        grads["b1"]=d_hidden.sum(axis=0)
        t+=1
        lr=.005/(1+.003*t)
        for key in weights:
            g=np.clip(grads[key],-2.,2.)
            moment[key]=.9*moment[key]+.1*g
            variance[key]=.999*variance[key]+.001*g*g
            m=moment[key]/(1-.9**t)
            v=variance[key]/(1-.999**t)
            weights[key]-=lr*m/(np.sqrt(v)+1.e-8)
        if (epoch+1)%10==0:
            hd=np.tanh(xd@weights["w1"]+weights["b1"])
            candidate=base_dev+hd@weights["w2"]+weights["b2"]
            dev_error=error(candidate,yd)
            if dev_error < best_dev*.995:
                best_dev=dev_error
                selected="geometry_ridge_plus_owned_residual"
                chosen_residual={key:value.copy() for key,value in weights.items()}

    # Official validation is scored ONCE, using the already frozen champion.
    mean=np.tile(y.mean(axis=0),(len(xv),1))
    ops=line_predict(xv[:,:OPS_DIM],operations_only)
    geometry=line_predict(xv,full_ridge)
    champion=geometry.copy()
    if selected=="geometry_ridge_plus_owned_residual":
        h=np.tanh(xv@chosen_residual["w1"]+chosen_residual["b1"])
        champion+=h@chosen_residual["w2"]+chosen_residual["b2"]
    mean_mse=error(mean,yv)
    ops_mse=error(ops,yv)
    geom_mse=error(geometry,yv)
    champion_mse=error(champion,yv)
    adv_indices=[i for i,r in enumerate(validation) if r["advanced"]]
    advanced={"count":len(adv_indices)}
    if len(adv_indices)>=8:
        advanced["operation_only_mse"]=error(ops[adv_indices],yv[adv_indices])
        advanced["geometry_student_mse"]=error(champion[adv_indices],yv[adv_indices])
    gains={"over_mean":(mean_mse-champion_mse)/mean_mse if mean_mse else 0.,
           "over_operations_only":(ops_mse-champion_mse)/ops_mse if ops_mse else 0.}
    accepted=(gains["over_mean"]>=.03 and
              gains["over_operations_only"]>=.02 and
              (len(adv_indices)<8 or
               advanced["geometry_student_mse"]<=advanced["operation_only_mse"]*1.02))
    report={
        "schema":"assetwright-deep-dino-geometry-curriculum-v2",
        "status":"validated_research_geometry_features" if accepted else "rejected_or_inconclusive",
        "train_sources":len(train),"internal_fit_sources":len(fitted),
        "internal_development_sources":len(development),
        "official_unseen_validation_sources":len(validation),
        "geometry_literal_coverage":round(coverage,6),
        "teacher":"frozen facebook/dinov2-small","views_per_source":4,
        "dataset_revision":train_doc["dataset_revision"],
        "selected_on_internal_development":selected,
        "selected_development_mse":round(best_dev,8),
        "operations_only_regularization":ops_reg,
        "geometry_regularization":full_reg,
        "heldout_constant_mean_mse":round(mean_mse,8),
        "heldout_operations_only_mse":round(ops_mse,8),
        "heldout_geometry_linear_mse":round(geom_mse,8),
        "heldout_selected_student_mse":round(champion_mse,8),
        "heldout_improvements":{k:round(v,6) for k,v in gains.items()},
        "advanced_operator_check":advanced,
        "official_validation_source_hashes_sha256":hashlib.sha256(
            "\n".join(sorted(r["hash"] for r in validation)).encode()).hexdigest(),
        "fitted_source_hashes_sha256":hashlib.sha256(
            "\n".join(sorted(r["hash"] for r in fitted)).encode()).hexdigest(),
        "actual_native_glb_geometry_scored":False,
        "teacher_produces_geometry":False,"android_deployed":False,
        "heldout_reused_for_hyperparameter_selection":False,
        "note":"CAD numeric literals improve visual-feature prediction only; not a validated shape generator.",
    }
    checkpoint={
        "schema":MODEL,"owner":"AssetWright-original",
        "source_revision":train_doc["dataset_revision"],
        "input":"supported_CAD_operations_plus_safe_numeric_literals",
        "input_dimensions":input_dim,"output":"24D_teacher_visual_signatures",
        "selected_model":selected,
        "linear_weights":full_ridge.tolist(),
        "residual_weights":({k:v.tolist() for k,v in chosen_residual.items()}
                            if selected=="geometry_ridge_plus_owned_residual" else None),
        "validated_on_official_split":accepted,
        "training_sources_sha256":report["fitted_source_hashes_sha256"],
        "teacher_required_at_inference":False,
        "android_deployable":False,
        "approved_for_geometry_generation":False,
    }
    return report,checkpoint


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("train","train-teacher","validation","validation-teacher","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    a=parser.parse_args()
    report,model=fit(*(json.loads(getattr(a,key).read_text())
                       for key in ("train","train_teacher","validation","validation_teacher")))
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (a.out/"candidate_student.json").write_text(json.dumps(model)+"\n")
    (a.out/"validated_research_student.json").unlink(missing_ok=True)
    if report["status"]=="validated_research_geometry_features":
        (a.out/"validated_research_student.json").write_text(json.dumps(model)+"\n")
    print(json.dumps(report,indent=2))
    if not model["validated_on_official_split"]:
        raise SystemExit("Geometry-aware candidate did not pass fresh validation gates")


if __name__=="__main__":
    main()

"""AssetWright own source-relative CAD profile -> real STL surface learner.

Unlike the first rejected 18-value aggregate student, this candidate reads
specific dimensionless sketch, extrusion, cut, hole, pattern and fillet
ratios from source AST. No downloaded CAD script is ever executed. STL data
is numerical supervision only, NOT a mesh generator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from cad_surface_profile_features import SIZE,SCHEMA as PROFILE_SCHEMA
from cad_surface_student import verify as verify_first,score,split_internal,features as original_features
from cad_surface_teacher import TARGETS

SCHEMA="assetwright-owned-cad-relative-surface-student-v2"

def verify(train,valid):
    a,b=verify_first(train,valid)
    for document,rows in ((train,a),(valid,b)):
        if document.get("profile_feature_schema")!=PROFILE_SCHEMA:
            raise ValueError("Missing safe relative-profile source schema")
        for row in rows:
            x=row.get("profile_geometry_features")
            if not isinstance(x,list) or len(x)!=SIZE or any(
                type(v) not in (int,float) or not np.isfinite(v) or
                v<-1 or v>4 for v in x):
                raise ValueError("Invalid source-only profile measurement")
    return a,b

def source_x(row,variant):
    if variant not in ("operations_only","aggregate_literals","relative_profile"):
        raise ValueError("Unknown CAD student comparison")
    baseline=np.asarray(original_features(row,variant!="operations_only"),dtype=np.float64)
    if variant=="relative_profile":
        return np.concatenate((baseline,np.asarray(row["profile_geometry_features"])))
    return baseline

def fit(rows,variant,ridge):
    x=np.stack([source_x(row,variant) for row in rows])
    y=np.stack([row["surface_target"] for row in rows])
    mx=x.mean(axis=0)
    sx=np.maximum(x.std(axis=0),.08)
    my=y.mean(axis=0)
    sy=np.maximum(y.std(axis=0),.08)
    z=np.column_stack((np.ones(len(x)),(x-mx)/sx))
    target=(y-my)/sy
    penalty=np.eye(z.shape[1])*ridge
    penalty[0,0]=0
    weights=np.linalg.solve(z.T@z+penalty,z.T@target)
    return {"source_features":variant,"ridge":ridge,
            "input_mean":mx.tolist(),"input_std":sx.tolist(),
            "target_mean":my.tolist(),"target_std":sy.tolist(),
            "coefficients":weights.tolist()}

def predict(model,rows):
    x=np.stack([source_x(row,model["source_features"]) for row in rows])
    a=(x-np.asarray(model["input_mean"]))/np.asarray(model["input_std"])
    z=np.column_stack((np.ones(len(x)),a))
    prediction=z@np.asarray(model["coefficients"])
    prediction=prediction*np.asarray(model["target_std"])+np.asarray(model["target_mean"])
    return np.maximum(0.,np.minimum(prediction,np.asarray([1,1,4,1,1])))

def run(trainfile:Path,validationfile:Path,out:Path):
    train_doc=json.loads(trainfile.read_text())
    validation_doc=json.loads(validationfile.read_text())
    train,validation=verify(train_doc,validation_doc)
    if train_doc["source_offset"]!=2300 or validation_doc["source_offset"]!=3700:
        raise ValueError("No reuse of prior exposed surface validation families")
    fit_rows,dev_rows=split_internal(train)
    options={}
    for variant in ("operations_only","aggregate_literals","relative_profile"):
        choices=[]
        for ridge in (1.,10.,40.,100.):
            model=fit(fit_rows,variant,ridge)
            error=score(predict(model,dev_rows),dev_rows)["scaled_surface_signature_mae"]
            choices.append((error,ridge))
        choices.sort()
        options[variant]=fit(fit_rows,variant,choices[0][1])
    # Official holdout used ONCE, after all three candidates are selected.
    scores={k:score(predict(v,validation),validation) for k,v in options.items()}
    median=np.median(np.stack([r["surface_target"] for r in fit_rows]),axis=0)
    prior=score(np.tile(median,(len(validation),1)),validation)
    ops=scores["operations_only"]["scaled_surface_signature_mae"]
    aggregate=scores["aggregate_literals"]["scaled_surface_signature_mae"]
    enriched=scores["relative_profile"]["scaled_surface_signature_mae"]
    baseline=prior["scaled_surface_signature_mae"]
    improvement_constant=1-enriched/baseline
    improvement_ops=1-enriched/ops
    improvement_old=1-enriched/aggregate
    improved=sum(scores["relative_profile"]["per_target_scaled_mae"][key]<
                 prior["per_target_scaled_mae"][key] for key in TARGETS)
    checks={
        "licensed_independent_STL_sources":True,
        "train_at_least_256":len(train)>=256,
        "fresh_validation_at_least_64":len(validation)>=64,
        "beats_train_median_by_five_percent":improvement_constant>=.05,
        "beats_strong_ops_only_by_one_point_five_percent":improvement_ops>=.015,
        "improves_at_least_three_physical_targets":improved>=3,
        "normalized_geometry_mae_at_most_point_eighteen":enriched<=.18,
        "richer_numeric_exceeds_old_aggregate_by_one_percent":improvement_old>=.01
    }
    approved=all(checks.values())
    report={
        "schema":"assetwright-relative-cad-stl-geometry-study-v2",
        "status":"passed_research_only" if approved else "rejected_research_candidate",
        "pinned_upstream_revision":train_doc["dataset_revision"],
        "license":train_doc["license"],
        "train_original_STL_sources":len(train),
        "fresh_official_validation_STL_sources":len(validation),
        "train_source_offset":2300,"validation_source_offset":3700,
        "teacher_only_licensed_STL_hashes":True,
        "internal_fit_sources":len(fit_rows),
        "internal_dev_sources":len(dev_rows),
        "baseline_train_median":prior,
        "operations_only":scores["operations_only"],
        "previous_aggregate_literals":scores["aggregate_literals"],
        "new_relative_profile_student":scores["relative_profile"],
        "relative_gain_vs_median":improvement_constant,
        "relative_gain_vs_operations":improvement_ops,
        "relative_gain_vs_old_aggregate":improvement_old,
        "per_target_improved_count":improved,
        "predeclared_learning_gates":checks,
        "native_GLBS_generated":0,"source_CadQuery_executed":False,
        "external_STL_used_as_final_geometry":False,
        "android_model_deployed":False,"human_approved":False,
        "limitations":"Only static numeric relationships from authored CAD programs; still no general geometry reconstruction, CAD fillets, G2 surface proof, or independent semantic design."
    }
    model={
        "schema":SCHEMA,"dataset_revision":train_doc["dataset_revision"],
        "teacher_source":"Apache-2.0 CAD binary STL descriptors",
        "source_feature_schema":PROFILE_SCHEMA,
        "student_type":"original regularized linear multivariate surface regressor",
        "weights":options["relative_profile"],
        "baseline_models":options,
        "training_STL_sha256_digest":hashlib.sha256("\n".join(sorted(
            row["stl_sha256"] for row in train)).encode()).hexdigest(),
        "source_ridge_selection":"train_internal_development_only",
        "production_deployable":False,"outside_AI_generated_final_model":False,
        "allows_imported_STL_as_output":False
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"candidate_profile_surface_student.json").write_text(json.dumps(model,indent=2)+"\n")
    print(json.dumps({
        "status":report["status"],
        "train":len(train),"validation":len(validation),
        "constant":baseline,"operations":ops,
        "old_aggregate":aggregate,"new_profile":enriched,"checks":checks
    },indent=2))
    if not approved:
        raise SystemExit("Richer CAD profile student rejected by original + new fixed gates")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train",type=Path,required=True)
    p.add_argument("--validation",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.train,a.validation,a.out)

if __name__=="__main__":main()

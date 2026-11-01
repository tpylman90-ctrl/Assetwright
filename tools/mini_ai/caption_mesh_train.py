"""Supervised caption-to-actual-mesh descriptor training, source-disjoint.

Unlike the publisher-dimensions learner, targets here are eight geometry
features measured from independently downloaded and inspected source meshes.
Nothing is deployed to the Android generator without geometry-specific tests.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from semantic_reference_search import words

MODEL_SCHEMA="assetwright-caption-mesh-descriptor-prior-v1"
REPORT_SCHEMA="assetwright-caption-mesh-training-report-v1"
DIMS=8
BUCKETS=256
MIN_PAIRS=32


def encode(text:str)->list[int]:
    vocab=set(words(text))
    return sorted({int(hashlib.blake2s(s.encode(),digest_size=4).hexdigest(),16)%BUCKETS for s in vocab})


def valid_rows(data:dict)->list[tuple[str,list[int],list[float]]]:
    if data.get("schema")!="assetwright-grounded-text-mesh-pairs-v1":
        raise ValueError("Invalid text/mesh source schema")
    ids=set()
    hashes=set()
    result=[]
    for row in data.get("pairs",[]):
        caption=row.get("caption")
        sha=row.get("source_mesh_sha256")
        id=row.get("source_object_id")
        vec=row.get("geometry_features")
        if not isinstance(caption,str) or len(caption.strip())<12:
            continue
        if not isinstance(sha,str) or len(sha)!=64 or not all(c in "0123456789abcdef" for c in sha):
            continue
        if not isinstance(id,str) or id in ids or sha in hashes:
            continue
        if row.get("license")!="CC0-1.0" or row.get("source")!="Poly Haven":
            continue
        if not isinstance(vec,list) or len(vec)!=DIMS or any(
            type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1 for x in vec
        ):
            continue
        x=encode(caption)
        if not x:
            continue
        ids.add(id);hashes.add(sha)
        result.append((sha,x,[float(v) for v in vec]))
    return sorted(result,key=lambda r:r[0])


def error(rows:list,weights:list[list[float]],bias:list[float])->float:
    total=0.0
    for _,features,target in rows:
        norm=math.sqrt(len(features))
        for k in range(DIMS):
            prediction=max(0.,min(1.,bias[k]+sum(weights[k][i] for i in features)/norm))
            total+=(prediction-target[k])**2
    return total/(len(rows)*DIMS)


def fit(dataset:dict)->tuple[dict,dict|None]:
    rows=valid_rows(dataset)
    report={"schema":REPORT_SCHEMA,"grounded_pairs":len(rows),
            "label_origin":"real Blender-measured CC0 source model features",
            "scope":"caption to numeric mesh descriptor; not topology or joints"}
    if len(rows)<MIN_PAIRS:
        return {**report,"status":"insufficient_real_mesh_pairs",
                "required_pairs":MIN_PAIRS},None
    train=[row for row in rows if int(row[0][:8],16)%5!=0]
    test=[row for row in rows if int(row[0][:8],16)%5==0]
    if len(train)<24 or len(test)<6:
        return {**report,"status":"insufficient_source_disjoint_holdout"},None
    bias=[sum(row[2][k] for row in train)/len(train) for k in range(DIMS)]
    w=[[0.0]*BUCKETS for _ in range(DIMS)]
    baseline=error(test,w,bias)
    for epoch in range(40):
        rate=.05/(1.+epoch*.14)
        for _,feat,target in train:
            scale=math.sqrt(len(feat))
            for k in range(DIMS):
                predicted=max(0.,min(1.,bias[k]+sum(w[k][i] for i in feat)/scale))
                delta=predicted-target[k]
                for i in feat:
                    w[k][i]-=rate*(delta/scale+.008*w[k][i])
    candidate=error(test,w,bias)
    passed=candidate < baseline*.97
    status="trained_passed_validation" if passed else "rejected_regression"
    summary={**report,"status":status,"train_models":len(train),
             "holdout_models":len(test),"baseline_mse":round(baseline,8),
             "candidate_mse":round(candidate,8),
             "improvement_fraction":round((baseline-candidate)/baseline,5) if baseline else 0}
    model={"schema":MODEL_SCHEMA,"method":"source-heldout hashed-caption SGD",
           "target":"8 Blender geometry measurements","feature_count":DIMS,
           "weight_buckets":BUCKETS,"bias":[round(v,6) for v in bias],
           "weights":[[round(v,6) for v in dimension] for dimension in w],
           "source_model_hashes":[row[0] for row in train],
           "android_deployable":False,"status":status}
    return summary,model


def run(source:Path,out:Path)->dict:
    doc=json.loads(source.read_text(encoding="utf-8"))
    report,model=fit(doc)
    out.mkdir(parents=True,exist_ok=True)
    (out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    if model is not None:
        (out/"candidate_prior.json").write_text(json.dumps(model,separators=(",",":"))+"\n",encoding="utf-8")
        if report["status"]=="trained_passed_validation":
            (out/"validated_prior.json").write_text(json.dumps(model,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return report


if __name__=="__main__":
    import argparse
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--pairs",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    args=cli.parse_args()
    run(args.pairs,args.out)

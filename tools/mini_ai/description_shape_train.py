"""Fit source-held-out text -> normalized 3D aspect-ratio priors.

Publisher descriptions, tags and object categories are features; Poly Haven's
published 3D dimensions are labels. This is real supervised learning of coarse
aspect ratios, not editable mesh generation or part-attachment understanding.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

from semantic_reference_search import words

SCHEMA="assetwright-description-aspect-prior-v1"
REPORT="assetwright-description-aspect-evaluation-v1"
DIMENSIONS=2
BUCKETS=512
MIN_RECORDS=60


def features(record:dict)->list[int]:
    title=record.get("name","")
    description=record.get("publisher_description","")
    tags=record.get("tags",[]) or []
    categories=record.get("category","").split("/")
    tokens=set(words(title+" "+description+" "+" ".join(tags)))
    for cat in categories:
        for w in words(cat):
            tokens.add("cat_"+w)
    return sorted({int.from_bytes(hashlib.blake2b(t.encode("utf-8"),digest_size=4).digest(),"little")%BUCKETS for t in tokens})


def rows_from_catalog(data:dict)->list[tuple[str,list[int],list[float]]]:
    if data.get("schema")!="assetwright-description-geometry-catalog-v1":
        raise ValueError("Wrong source corpus")
    rows=[]
    for item in data.get("records",[]):
        target=item.get("dimension_ratios")
        if item.get("license")!="CC0-1.0":
            continue
        if not isinstance(target,list) or len(target)!=2 or any(
            type(v) not in (int,float) or not math.isfinite(v) or not 0<v<=1 for v in target
        ):
            continue
        if not (item.get("publisher_description") or "").strip():
            continue
        feat=features(item)
        if not feat:
            continue
        rows.append((item["id"],feat,[float(t) for t in target]))
    return sorted(rows,key=lambda r:r[0])


def mse(rows:list,weights:list[list[float]],bias:list[float])->float:
    if not rows:
        raise ValueError("Empty evaluation set")
    total=0.
    for _,feat,target in rows:
        scale=math.sqrt(len(feat))
        for k in range(DIMENSIONS):
            guess=max(0.,min(1.,bias[k]+sum(weights[k][i] for i in feat)/scale))
            total+=(guess-target[k])**2
    return total/(len(rows)*DIMENSIONS)


def fit(data:dict)->tuple[dict,dict|None]:
    records=rows_from_catalog(data)
    common={"schema":REPORT,"source":"Poly Haven CC0","licensed_labeled_objects":len(records),
            "scope":"publisher description and category -> sorted 3D bounding-axis ratios; no mesh or topology training"}
    if len(records)<MIN_RECORDS:
        return {**common,"status":"insufficient_described_dimensions",
                "minimum_required":MIN_RECORDS},None
    # Group-disjoint deterministic split: a model appears only in one split.
    testing=[r for r in records if int(hashlib.sha256(r[0].encode()).hexdigest(),16)%5==0]
    training=[r for r in records if int(hashlib.sha256(r[0].encode()).hexdigest(),16)%5!=0]
    if len(testing)<10 or len(training)<40:
        return {**common,"status":"insufficient_holdout"},None
    b=[sum(row[2][k] for row in training)/len(training) for k in range(DIMENSIONS)]
    baseline_weights=[[0.]*BUCKETS for _ in range(DIMENSIONS)]
    baseline=mse(testing,baseline_weights,b)
    w=[[0.]*BUCKETS for _ in range(DIMENSIONS)]
    # Deterministic bounded SGD, ridge penalty and shrinkage; no external ML.
    for epoch in range(30):
        rate=.045/(1.+epoch*.12)
        for _,feat,target in training:
            scale=math.sqrt(len(feat))
            for k in range(DIMENSIONS):
                prediction=max(0.,min(1.,b[k]+sum(w[k][i] for i in feat)/scale))
                err=prediction-target[k]
                for i in feat:
                    w[k][i]-=rate*(err/scale+.004*w[k][i])
    predicted=mse(testing,w,b)
    passed=predicted<baseline-.00001
    report={**common,"status":"trained_passed_validation" if passed else "rejected_regression",
            "train_objects":len(training),"heldout_objects":len(testing),
            "baseline_mse":round(baseline,8),"candidate_mse":round(predicted,8),
            "improvement_fraction":round((baseline-predicted)/baseline,5) if baseline else 0}
    model={"schema":SCHEMA,"method":"regularized hashed-word SGD regression",
           "feature_buckets":BUCKETS,"target_order":["smallest_over_largest","middle_over_largest"],
           "weights":[[round(x,6) for x in arr] for arr in w],
           "bias":[round(v,6) for v in b],
           "train_objects":len(training),
           "source":"Poly Haven CC0 publisher metadata",
           "review_status":"coarse aspect-ratio prior only",
           "android_deployable":False}
    return report,model


def run(source:Path,out:Path)->dict:
    corpus=json.loads(source.read_text(encoding="utf-8"))
    report,model=fit(corpus)
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
    cli.add_argument("--catalog",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    args=cli.parse_args()
    run(args.catalog,args.out)

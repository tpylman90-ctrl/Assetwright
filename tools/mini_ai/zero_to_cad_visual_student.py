"""Distill frozen DINOv2 features into an ORIGINAL AssetWright CAD recipe model.

The teacher supplies numeric shape targets during training only. At inference
the student reads CAD operation sequences, not DINO features or external meshes.
This research model predicts signatures, not native GLB geometry.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
from zero_to_cad_ingest import OPS
from zero_to_cad_dinov2_teacher import SCHEMA as TEACHER_SCHEMA,MODEL as TEACHER
from zero_to_cad_operation_student import read_rows
from visual_transfer_student import project_teacher

MODEL="assetwright-owned-cad-visual-distillation-v1"
TOKENS=sorted(OPS)
BUCKETS=48
DIM=len(TOKENS)+BUCKETS+2
OUTPUTS=24

def input_features(operations:list[str],nfaces:object)->list[float]:
    if not isinstance(operations,list) or not 3<=len(operations)<=128 or any(op not in OPS for op in operations):
        raise ValueError("Unsupported CAD construction sequence")
    x=[0.]*DIM
    for op in operations: x[TOKENS.index(op)]+=1/math.sqrt(len(operations))
    for a,b in zip(operations,operations[1:]):
        i=int(hashlib.sha256(f"{a}:{b}".encode()).hexdigest()[:8],16)%BUCKETS
        x[len(TOKENS)+i]+=1/math.sqrt(len(operations))
    x[-2]=math.log1p(len(operations))/5
    if isinstance(nfaces,int) and not isinstance(nfaces,bool) and 0<nfaces<100000:
        x[-1]=math.log1p(nfaces)/12
    return x

def prepared(manifest:dict,teacher:dict,split:str)->list[dict]:
    records=read_rows(manifest,split)
    if (teacher.get("schema")!=TEACHER_SCHEMA or teacher.get("model_id")!=TEACHER or
        teacher.get("teacher_frozen") is not True):
        raise ValueError("Unapproved frozen teacher")
    if teacher.get("source_dataset")!=manifest["dataset"] or teacher.get("source_split")!=split:
        raise ValueError("Teacher dataset/split mismatch")
    lookup={}
    for item in teacher.get("records",[]):
        key=item.get("source_id")
        if key in lookup: raise ValueError("Repeated teacher sample")
        lookup[key]=item
    output=[]
    for item in records:
        teacher_row=lookup.get(item["source_id"])
        if (teacher_row is None or
            teacher_row.get("code_sha256")!=item["code_sha256"] or
            teacher_row.get("view_sha256")!=item.get("view_sha256")):
            raise ValueError("Unverified image/source alignment")
        output.append({"source_id":item["source_id"],"hash":item["code_sha256"],
                       "x":input_features(item["operations"],item.get("num_faces")),
                       "y":project_teacher(teacher_row.get("frozen_visual_embedding"))})
    if len(output)!=len(lookup): raise ValueError("Unaccounted for teacher samples")
    return output

def predict(weights:list[list[float]],bias:list[float],x:list[float])->list[float]:
    return [math.tanh(b+sum(wi*xi for wi,xi in zip(row,x)))
            for row,b in zip(weights,bias)]

def mse(samples:list[dict],weights:list[list[float]]|None,bias:list[float])->float:
    total=0.
    for sample in samples:
        guess=predict(weights,bias,sample["x"]) if weights is not None else bias
        total+=sum((a-b)**2 for a,b in zip(guess,sample["y"]))
    return total/(len(samples)*OUTPUTS)

def fit(train_doc:dict,train_teacher:dict,valid_doc:dict,valid_teacher:dict)->tuple[dict,dict|None]:
    train=prepared(train_doc,train_teacher,"train")
    heldout=prepared(valid_doc,valid_teacher,"validation")
    common={"schema":"assetwright-cad-visual-distillation-report-v1",
            "train_sources":len(train),"heldout_sources":len(heldout),
            "teacher":"frozen "+TEACHER,
            "output":"24-D numeric shape signature; never 3D meshes",
            "teacher_required_at_inference":False,
            "android_deployable":False}
    ids={r["source_id"] for r in train};hashes={r["hash"] for r in train}
    if any(r["source_id"] in ids or r["hash"] in hashes for r in heldout):
        raise ValueError("CAD distillation train/validation leakage")
    if len(train)<24 or len(heldout)<8:
        return {**common,"status":"insufficient_aligned_sources"},None
    baseline=[sum(p["y"][i] for p in train)/len(train) for i in range(OUTPUTS)]
    before=mse(heldout,None,baseline)
    weights=[[0.]*DIM for _ in range(OUTPUTS)]
    bias=baseline[:]
    rng=random.Random(144)
    for epoch in range(120):
        lr=.027/(1+.018*epoch)
        batch=train[:]
        rng.shuffle(batch)
        for point in batch:
            values=predict(weights,bias,point["x"])
            for o in range(OUTPUTS):
                d=2*(values[o]-point["y"][o])*(1-values[o]**2)/OUTPUTS
                bias[o]-=lr*d
                for i,value in enumerate(point["x"]):
                    if value: weights[o][i]-=lr*(d*value+.001*weights[o][i])
    after=mse(heldout,weights,bias)
    gain=(before-after)/before if before else 0.
    passed=after<before*.97
    report={**common,"status":"validated_research_visual_student" if passed else "visual_student_rejected_holdout",
            "baseline_mean_mse":round(before,8),"owned_student_mse":round(after,8),
            "heldout_improvement_fraction":round(gain,6),
            "note":"Visual shape signature learning, NOT final CAD or mobile-ready generation."}
    model={"schema":MODEL,"teacher":"frozen "+TEACHER,
           "input":"source_cad_operation_sequence","inference_needs_teacher":False,
           "output":"24_DINO_projected_features","operations":TOKENS,
           "weights":weights,"bias":bias,"android_deployable":False,
           "approved_for_geometry_generation":False,"validated_on_official_split":passed}
    return report,model

def run(files:list[Path],out:Path)->dict:
    train,tfeat,valid,vfeat=(json.loads(p.read_text()) for p in files)
    report,model=fit(train,tfeat,valid,vfeat)
    out.mkdir(parents=True,exist_ok=True)
    (out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"validated_visual_student.json").unlink(missing_ok=True)
    if model is not None:
        (out/"candidate_visual_student.json").write_text(json.dumps(model,separators=(",",":"))+"\n")
        if report["status"]=="validated_research_visual_student":
            (out/"validated_visual_student.json").write_text(json.dumps(model,separators=(",",":"))+"\n")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("train","train-teacher","validation","validation-teacher","out"):
        p.add_argument("--"+flag,type=Path,required=True)
    a=p.parse_args()
    files=[a.train,a.train_teacher,a.validation,a.validation_teacher]
    print(json.dumps(run(files,a.out),indent=2))
if __name__=="__main__": main()

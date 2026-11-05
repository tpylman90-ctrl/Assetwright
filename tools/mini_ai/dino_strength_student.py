"""Eight independent matched CPU sessions for native strength calibration.

Original AssetWright Mini AI sees only fixed-camera before/after pixels.
Frozen DINOv2 is auxiliary supervision on training examples, never an
inference dependency or source of generated GLBs. Research-only.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from advanced_form_student import OPERATIONS
from dino_delta_school import (DINO, TEACHER, FAMILIES, LEVELS, STUDY,
                               checked_manifest)
from dino_delta_student import INPUT_DIM, image_features

SCHEMA="assetwright-original-multisession-native-strength-v2"
RESULT_SCHEMA="assetwright-multisession-strength-calibration-evaluation-v2"
PROPOSALS="assetwright-multisession-native-strength-proposals-v2"
SEEDS=(131, 719, 1019, 2029, 3253, 4027, 5419, 8209)
HIDDEN=96
EPOCHS=260


def aligned(manifest:dict,teacher:dict,images:Path)->list[dict]:
    if STUDY!="strength_v2":
        raise ValueError("Run strength calibration with explicit strength_v2 study isolation")
    source=checked_manifest(manifest,images)
    if (teacher.get("schema")!=TEACHER or teacher.get("teacher")!=DINO
        or teacher.get("teacher_frozen") is not True
        or teacher.get("teacher_generates_3d") is not False):
        raise ValueError("Unverified frozen visual difference teacher")
    lessons=teacher.get("examples")
    if not isinstance(lessons,list) or len(lessons)!=len(source):
        raise ValueError("Missing teacher/source paired example inventory")
    lookup={}
    for t in lessons:
        key=t.get("case")
        if not isinstance(key,str) or key in lookup:
            raise ValueError("Duplicate DINO source record")
        lookup[key]=t
    out=[];hashes=set()
    for row in source:
        t=lookup.get(row["case"])
        if t is None or any(t.get(key)!=row[key] for key in (
            "baseline_glb_sha256","modified_glb_sha256",
            "before_view_sha256","after_view_sha256")):
            raise ValueError("Cross-source image/GLB/teacher mismatch")
        signature=t.get("frozen_dino_delta_signature")
        if (not isinstance(signature,list) or len(signature)!=24 or
            any(type(x) not in (float,int) or not math.isfinite(x)
                or abs(x)>1.1 for x in signature)):
            raise ValueError("Unbounded DINO difference feature")
        image=image_features(row,images)
        if len(image)!=INPUT_DIM or any(not math.isfinite(v) for v in image):
            raise ValueError("Malformed owned image feature")
        source_hash=row["modified_glb_sha256"]
        if source_hash in hashes:
            raise ValueError("Native target geometry repeated across source cohorts")
        hashes.add(source_hash)
        out.append({
            "case":row["case"],"family":row["family"],
            "split":row["split"],"operation":row["operation"],
            "strength":row["strength"],"source_hash":source_hash,
            "baseline_hash":row["baseline_glb_sha256"],
            "dimensions":{key:row[key] for key in ("length","width","height")},
            "pixel":image,
            "morph":row["measured_morphology_delta"],
            "teacher":signature,
        })
    train=[r for r in out if r["split"]=="train"]
    dev=[r for r in out if r["split"]=="development"]
    blind=[r for r in out if r["split"]=="validation"]
    if (len(out),len(train),len(dev),len(blind))!=(948,756,96,96):
        raise ValueError("Not enough new independent native strength examples")
    for left,right in (("train","development"),("train","validation"),
                       ("development","validation")):
        if set(FAMILIES[left])&set(FAMILIES[right]) or set(LEVELS[left])&set(LEVELS[right]):
            raise ValueError("Known development/final strength cohort leaked")
    return out


def fit(manifest:dict,teacher:dict,images:Path)->tuple[dict,dict,dict]:
    import numpy as np
    import torch
    from torch import nn
    import torch.nn.functional as F

    records=aligned(manifest,teacher,images)
    groups={split:[row for row in records if row["split"]==split]
            for split in ("train","development","validation")}
    torch.set_num_threads(min(2,torch.get_num_threads()))
    training=groups["train"]
    original_x=np.asarray([r["pixel"] for r in training],dtype=np.float32)
    center=original_x.mean(axis=0)
    scale=np.maximum(original_x.std(axis=0),.06)
    geom=np.asarray([r["morph"] for r in training],dtype=np.float32)
    geom_scale=np.maximum(geom.std(axis=0),.08)

    def data(split):
        rows=groups[split]
        values=(np.asarray([r["pixel"] for r in rows],dtype=np.float32)-center)/scale
        return (
            torch.tensor(values,dtype=torch.float32),
            torch.tensor([OPERATIONS.index(r["operation"]) for r in rows],dtype=torch.long),
            torch.tensor([r["strength"] for r in rows],dtype=torch.float32),
            torch.tensor(np.asarray([r["morph"] for r in rows],dtype=np.float32)/geom_scale),
            torch.tensor([r["teacher"] for r in rows],dtype=torch.float32)
        )
    train=data("train")
    development=data("development")
    blind=data("validation")
    order={}
    for idx,row in enumerate(training):
        order.setdefault((row["family"],row["operation"]),[]).append(
            (row["strength"],idx))
    low=[];high=[]
    for levels in order.values():
        levels=sorted(levels)
        if len(levels)!=7:
            raise ValueError("Incomplete training range of native strength levels")
        low.extend(levels[i][1] for i in range(len(levels)-1))
        high.extend(levels[i+1][1] for i in range(len(levels)-1))
    lower=torch.tensor(low,dtype=torch.long)
    upper=torch.tensor(high,dtype=torch.long)

    class Student(nn.Module):
        def __init__(self):
            super().__init__()
            self.body=nn.Sequential(nn.Linear(INPUT_DIM,HIDDEN),nn.Tanh())
            self.operation=nn.Linear(HIDDEN,len(OPERATIONS))
            self.strength_by_operation=nn.Linear(HIDDEN,len(OPERATIONS))
            self.geometry=nn.Linear(HIDDEN,6)
            self.dino_visual=nn.Linear(HIDDEN,24)
        def forward(self,x):
            hidden=self.body(x)
            return (self.operation(hidden),
                    torch.sigmoid(self.strength_by_operation(hidden)),
                    self.geometry(hidden),self.dino_visual(hidden))

    def score(model,batch):
        model.eval()
        pixels,operation,strength,_,_=batch
        with torch.inference_mode():
            logits,heads,_,_=model(pixels)
            guess=logits.argmax(dim=1)
            inferred=heads.gather(1,guess[:,None]).squeeze(1)
            oracle=heads.gather(1,operation[:,None]).squeeze(1)
            mae=float((inferred-strength).abs().mean())
            operator_accuracy=float((guess==operation).float().mean())
            return {
                "accuracy":operator_accuracy,"strength_mae":mae,
                "oracle_operation_strength_mae":float((oracle-strength).abs().mean()),
                "operator_cross_entropy":float(F.cross_entropy(logits,operation)),
                "development_priority":float(
                    3.5*(inferred-strength).abs().mean()+
                    .45*F.cross_entropy(logits,operation)),
                "per_operator":{
                    op:{"correct":int(((guess==i)&(operation==i)).sum()),
                        "total":int((operation==i).sum()),
                        "strength_mae":float((inferred[operation==i]-
                                              strength[operation==i]).abs().mean())}
                    for i,op in enumerate(OPERATIONS)
                }
            }

    def single_session(seed:int,*,teacher_on:bool):
        torch.manual_seed(seed)
        model=Student()
        optimizer=torch.optim.AdamW(model.parameters(),lr=.003,
                                     weight_decay=.0008)
        x,ops,strength,morph,target=train
        best=None;best_score=float("inf");best_epoch=0;last=None
        for epoch in range(EPOCHS):
            model.train()
            logits,heads,shape,visual=model(x)
            true_head=heads.gather(1,ops[:,None]).squeeze(1)
            # Stage 1: recognize ops; stage 2: learn continuous effect size;
            # stage 3: fine tune effect size and enforce monotonic response.
            op_weight=1.2 if epoch<65 else (.8 if epoch<170 else .6)
            size_weight=2. if epoch<65 else (5.0 if epoch<170 else 7.0)
            loss=op_weight*F.cross_entropy(logits,ops)
            loss+=size_weight*F.smooth_l1_loss(true_head,strength,beta=.10)
            loss+=.18*F.smooth_l1_loss(shape,morph)
            if epoch>=65:
                # A larger true transformation should never map to a
                # smaller predicted strength within a source family+op.
                loss+=.5*F.relu(.012-(true_head[upper]-true_head[lower])).mean()
            if teacher_on:
                loss+=.65*F.mse_loss(visual,target)
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),2.)
            optimizer.step()
            if (epoch+1)%5==0:
                m=score(model,development)
                if m["development_priority"]<best_score:
                    best_score=m["development_priority"]
                    best_epoch=epoch+1
                    best=copy.deepcopy(model.state_dict())
                    last=m
        if best is None:
            raise ValueError("Unable to select owned training session")
        model.load_state_dict(best)
        return model,{
            "seed":seed,"frozen_teacher_used_in_loss":teacher_on,
            "selected_epoch":best_epoch,
            "best_development_priority":round(best_score,8),
            "development_accuracy":round(last["accuracy"],6),
            "development_strength_mae":round(last["strength_mae"],6)
        }

    histories={"teacher_free":[],"DINO_guided":[]}
    winners={}
    for key,teacher_on in (("teacher_free",False),("DINO_guided",True)):
        best=None;best_score=float("inf");best_model=None
        for seed in SEEDS:
            model,history=single_session(seed,teacher_on=teacher_on)
            histories[key].append(history)
            if history["best_development_priority"]<best_score:
                best_score=history["best_development_priority"]
                best=history
                best_model=model
        winners[key]=best_model
        histories[key+"_winner"]=best

    # Both champions have been frozen using development data. Only now
    # evaluate the never-inspected bs_blind01..04 cohort, exactly once.
    metrics={key:score(model,blind) for key,model in winners.items()}
    baseline=metrics["teacher_free"]
    guided=metrics["DINO_guided"]
    def improvement(a,b):
        return (a-b)/a if a>0 else 0.0
    gain_mae=improvement(baseline["strength_mae"],guided["strength_mae"])
    same_or_better=(
        guided["accuracy"]>=.65 and guided["strength_mae"]<=.18
        and guided["strength_mae"]<=baseline["strength_mae"]-.008
        and guided["accuracy"]>=baseline["accuracy"]-.03
    )
    heldout=groups["validation"]
    sha=hashlib.sha256("\n".join(sorted(
        row["source_hash"] for row in heldout)).encode()).hexdigest()
    report={
        "schema":RESULT_SCHEMA,
        "status":"provisional_strength_student_pass" if same_or_better else "strength_calibration_not_yet_validated",
        "source_kotlin_native_glbs":974,
        "source_before_after_changes":948,
        "training_examples":756,"development_examples":96,
        "untouched_validation_examples":96,
        "independent_seeds_per_condition":len(SEEDS),
        "total_independent_training_sessions":2*len(SEEDS),
        "epochs_per_session_max":EPOCHS,
        "training_method":"three-stage operator recognition + per-operation strength heads + monotonic ranking",
        "source_family_and_strength_holdouts_disjoint":True,
        "teacher":"frozen "+DINO,
        "external_AI_produces_3d":False,
        "teacher_used_during_inference":False,
        "source_modified_sha256_validation":sha,
        "development_only_seed_and_epoch_selection":histories,
        "heldout":metrics,
        "DINO_strength_error_reduction_fraction":gain_mae,
        "native_GLBs_reconstructed":False,
        "approved_for_Android":False,
        "note":"More training is not proof of improvement; independently compare against same-session teacher-free control and native GLBs."
    }

    proposals={"schema":PROPOSALS,
               "no_external_meshes":True,
               "original_validation_source_hash":sha,
               "teacher_free":[],"DINO_guided":[]}
    for key,model in winners.items():
        model.eval()
        with torch.inference_mode():
            logits,heads,_,_=model(blind[0])
            chosen=logits.argmax(dim=1)
            power=heads.gather(1,chosen[:,None]).squeeze(1)
        for i,row in enumerate(heldout):
            proposals[key].append({
                "case":row["case"],
                "source_glb_sha256":row["source_hash"],
                "baseline_glb_sha256":row["baseline_hash"],
                "predicted_operation":OPERATIONS[int(chosen[i])],
                "predicted_strength":round(float(power[i]),7),
                **row["dimensions"]
            })
    original=winners["DINO_guided"]
    model_package={
        "schema":SCHEMA,
        "owned_generator":"AssetWright-Kotlin-AdvancedFormLab",
        "input":"label_free_before_after_fixed_camera_pixels",
        "image_feature_dim":INPUT_DIM,
        "hidden_dim":HIDDEN,
        "supported_operations":list(OPERATIONS),
        "train_only_feature_mean":center.tolist(),
        "train_only_feature_sd":scale.tolist(),
        "train_only_morphology_sd":geom_scale.tolist(),
        "teacher_frozen_at_training":True,
        "teacher_needed_at_inference":False,
        "selected_session_seed":histories["DINO_guided_winner"]["seed"],
        "original_student_weights":{
            key:value.detach().cpu().tolist()
            for key,value in original.state_dict().items()
        },
        "source_hash_validation":sha,
        "provisional_research_quality":same_or_better,
        "android_deployable":False,
        "approved_for_geometry_generation":False
    }
    return report,model_package,proposals


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("manifest","teacher","images","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    args=parser.parse_args()
    report,model,proposals=fit(
        json.loads(args.manifest.read_text()),
        json.loads(args.teacher.read_text()),
        args.images)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (args.out/"candidate_student.json").write_text(json.dumps(model,separators=(",",":"))+"\n")
    (args.out/"student_proposals.json").write_text(json.dumps(proposals,indent=2)+"\n")
    output=["schema="+PROPOSALS,"external_mesh_used=false","count=96"]
    for variant in ("teacher_free","DINO_guided"):
        for i,row in enumerate(proposals[variant]):
            for key,value in row.items():
                output.append(f"{variant}.{i}.{key}={value}")
    (args.out/"native_proposals.properties").write_text("\n".join(output)+"\n")
    print(json.dumps({
        "status":report["status"],
        "training_examples":report["training_examples"],
        "completed_sessions":report["total_independent_training_sessions"],
        "winner_sessions":{k:v for k,v in report["development_only_seed_and_epoch_selection"].items()
                           if k.endswith("_winner")},
        "heldout":report["heldout"],
        "model_promoted_to_android":False
    },indent=2))


if __name__=="__main__":
    main()

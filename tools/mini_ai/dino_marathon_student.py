"""Compute-budgeted 32-minute ORIGINAL Mini AI geometry-strength training.

Do not change the heldout families, use a pretrained model at inference,
or substitute visual embeddings for actual Kotlin GLB reconstruction.
DINOv2 is a FROZEN auxiliary training teacher only.

Eight individually seeded DINO-student trials and eight matched controls.
Each session *trains* for its prescribed wall-clock budget and saves its
best DEVELOPMENT-only checkpoint (safetensors, no pickle). A result can be
rejected despite an otherwise successful 32-minute training run.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import time

from advanced_form_student import OPERATIONS
from dino_delta_school import FAMILIES,LEVELS,STUDY,TEACHER,DINO,checked_manifest
from dino_delta_student import INPUT_DIM,image_features

STUDENT_SCHEMA="assetwright-own-marathon-strength-student-v3"
EVALUATION_SCHEMA="assetwright-32min-strength-student-evaluation-v3"
PROPOSAL_SCHEMA="assetwright-marathon-native-strength-proposals-v3"
SEEDS=(131,719,1019,2029,3253,4027,5419,8209)
INPUTS=INPUT_DIM
HIDDEN=96


def source_aligned(manifest,teacher,images):
    if STUDY!="strength_marathon_v3":
        raise ValueError("Must activate isolated and never-inspected v3 study")
    rows=checked_manifest(manifest,images)
    lessons=teacher.get("examples")
    if not (teacher.get("schema")==TEACHER
            and teacher.get("teacher")==DINO
            and teacher.get("teacher_frozen") is True
            and teacher.get("teacher_generates_3d") is False
            and isinstance(lessons,list) and len(lessons)==len(rows)):
        raise ValueError("Teacher or original mesh provenance incomplete")
    lookup={}
    for lesson in lessons:
        key=lesson.get("case")
        if not isinstance(key,str) or key in lookup:
            raise ValueError("Unknown or duplicate frozen teacher lesson")
        lookup[key]=lesson
    aligned=[];verified=set()
    for row in rows:
        lesson=lookup.get(row["case"])
        if lesson is None or any(lesson.get(k)!=row[k] for k in (
            "baseline_glb_sha256","modified_glb_sha256",
            "before_view_sha256","after_view_sha256")):
            raise ValueError("Frozen DINO feature not aligned to source/after GLB hashes")
        signature=lesson.get("frozen_dino_delta_signature")
        if (not isinstance(signature,list) or len(signature)!=24 or
            any(type(x) not in (float,int) or not math.isfinite(x)
                or abs(x)>1.1 for x in signature)):
            raise ValueError("Unbounded frozen DINO visual feature")
        source_hash=row["modified_glb_sha256"]
        if source_hash in verified:
            raise ValueError("Duplicate original native target source")
        verified.add(source_hash)
        pixels=image_features(row,images)
        if len(pixels)!=INPUTS or any(not math.isfinite(v) for v in pixels):
            raise ValueError("Bad owned pixel pair")
        aligned.append({
            "case":row["case"],"family":row["family"],
            "split":row["split"],"op":row["operation"],
            "strength":row["strength"],
            "original_sha256":source_hash,
            "baseline_sha256":row["baseline_glb_sha256"],
            "dimensions":{k:row[k] for k in ("length","width","height")},
            "x":pixels,"teacher":signature,
            "morph":row["measured_morphology_delta"]
        })
    sizes={p:sum(r["split"]==p for r in aligned)
           for p in ("train","development","validation")}
    if sizes!={"train":672,"development":96,"validation":96}:
        raise ValueError("Incorrect 864 original before/after source changes")
    for a,b in (("train","development"),("train","validation"),
                ("development","validation")):
        if set(FAMILIES[a])&set(FAMILIES[b]) or set(LEVELS[a])&set(LEVELS[b]):
            raise ValueError("New source family or strength leakage")
    return aligned


def fit(manifest,teacher,images,out,optimization_seconds):
    import numpy as np
    import torch
    from torch import nn
    import torch.nn.functional as F
    from safetensors.torch import save_file
    if not 1800<=optimization_seconds<=2100:
        raise ValueError("Explicit compute budget must be 30-35 minutes")
    rows=source_aligned(manifest,teacher,images)
    groups={phase:[r for r in rows if r["split"]==phase]
            for phase in ("train","development","validation")}
    torch.set_num_threads(min(2,torch.get_num_threads()))
    training=groups["train"]
    x_train=np.asarray([r["x"] for r in training],dtype=np.float32)
    means=x_train.mean(axis=0)
    scales=np.maximum(x_train.std(axis=0),.06)
    morphology=np.asarray([r["morph"] for r in training],dtype=np.float32)
    m_scales=np.maximum(morphology.std(axis=0),.07)

    def tensors(phase):
        batch=groups[phase]
        return (
            torch.tensor((np.asarray([r["x"] for r in batch],dtype=np.float32)
                          -means)/scales,dtype=torch.float32),
            torch.tensor([OPERATIONS.index(r["op"]) for r in batch],dtype=torch.long),
            torch.tensor([r["strength"] for r in batch],dtype=torch.float32),
            torch.tensor(np.asarray([r["morph"] for r in batch],dtype=np.float32)
                         /m_scales,dtype=torch.float32),
            torch.tensor([r["teacher"] for r in batch],dtype=torch.float32),
        )
    train=tensors("train")
    development=tensors("development")
    ranking={}
    for i,row in enumerate(training):
        ranking.setdefault((row["family"],row["op"]),[]).append(
            (row["strength"],i))
    low=[];high=[]
    for group in ranking.values():
        group.sort()
        if len(group)!=7:
            raise ValueError("Incomplete native training strength ordering")
        for i in range(6):
            low.append(group[i][1])
            high.append(group[i+1][1])
    lower=torch.tensor(low,dtype=torch.long)
    upper=torch.tensor(high,dtype=torch.long)

    class Student(nn.Module):
        def __init__(self):
            super().__init__()
            self.core=nn.Sequential(
                nn.Linear(INPUTS,HIDDEN),nn.Tanh(),
                nn.Linear(HIDDEN,HIDDEN),nn.Tanh())
            self.op=nn.Linear(HIDDEN,len(OPERATIONS))
            self.strength=nn.Linear(HIDDEN,len(OPERATIONS))
            self.physical=nn.Linear(HIDDEN,6)
            self.dino=nn.Linear(HIDDEN,24)
        def forward(self,x):
            z=self.core(x)
            return self.op(z),torch.sigmoid(self.strength(z)),self.physical(z),self.dino(z)

    def evaluate(model,batch):
        model.eval()
        x,op,truth,_,_=batch
        with torch.inference_mode():
            scores,powers,_,_=model(x)
            chosen=scores.argmax(dim=1)
            selected=powers.gather(1,chosen[:,None]).flatten()
            oracle=powers.gather(1,op[:,None]).flatten()
            accuracy=float((chosen==op).float().mean())
            mae=float((selected-truth).abs().mean())
            per_op={
                tag:{
                    "correct":int(((chosen==i)&(op==i)).sum()),
                    "total":int((op==i).sum()),
                    "strength_mae":float((selected[op==i]-
                                          truth[op==i]).abs().mean())
                } for i,tag in enumerate(OPERATIONS)}
            return {
                "accuracy":accuracy,
                "strength_mae":mae,
                "oracle_strength_mae":float((oracle-truth).abs().mean()),
                "operator_ce":float(F.cross_entropy(scores,op)),
                "development_priority":3.75*mae+.48*float(F.cross_entropy(scores,op)),
                "per_operation":per_op
            }

    out.mkdir(parents=True,exist_ok=True)
    archive=out/"seed_checkpoints"
    archive.mkdir(parents=True,exist_ok=True)
    session_budget=optimization_seconds/(2*len(SEEDS))
    history={"teacher_free":[],"DINO_guided":[]}
    winners={}
    compute_total=0.
    for label,teacher_on in (("teacher_free",False),("DINO_guided",True)):
        winner=None;winning_priority=float("inf");best_seed=None
        for seed in SEEDS:
            torch.manual_seed(seed)
            student=Student()
            optimizer=torch.optim.AdamW(student.parameters(),lr=.0025,weight_decay=.0008)
            batch_x,batch_op,batch_strength,batch_morph,batch_teacher=train
            best_state=None;best_loss=float("inf");best_step=0
            step=0
            session_start=time.perf_counter()
            deadline=session_start+session_budget
            checkpoint_every=70
            last_log=session_start
            while time.perf_counter()<deadline or step<checkpoint_every:
                student.train()
                # Real SGD updates, seeded differently every session.
                indices=torch.randint(len(training),(128,))
                # Small physically label-preserving camera/photon noise
                # builds resilience; never changes geometry supervision.
                jitter=.01+.020*(step%7)/6.
                observations=batch_x[indices]+jitter*torch.randn_like(batch_x[indices])
                truth_op=batch_op[indices]
                op_score,strength_heads,morph_prediction,vision_prediction=student(observations)
                truth_strength=strength_heads.gather(1,truth_op[:,None]).flatten()
                progress=min(1.0,(time.perf_counter()-session_start)/session_budget)
                strength_weight=3.5+5.0*progress
                class_weight=1.0-.40*progress
                loss=class_weight*F.cross_entropy(op_score,truth_op)
                loss+=strength_weight*F.smooth_l1_loss(
                    truth_strength,batch_strength[indices],beta=.09)
                loss+=.12*F.smooth_l1_loss(morph_prediction,batch_morph[indices],beta=.20)
                if teacher_on:
                    loss+=.55*F.mse_loss(vision_prediction,batch_teacher[indices])
                pair=torch.randint(len(lower),(48,))
                lo=lower[pair];hi=upper[pair]
                # Penalize reversing physical control magnitude within
                # the SAME object and native operator.
                p_lo=student(batch_x[lo])[1].gather(1,batch_op[lo][:,None]).flatten()
                p_hi=student(batch_x[hi])[1].gather(1,batch_op[hi][:,None]).flatten()
                loss+=(1.0+.5*progress)*F.relu(.01-(p_hi-p_lo)).mean()
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(student.parameters(),2.0)
                optimizer.step()
                step+=1
                if step%checkpoint_every==0:
                    score=evaluate(student,development)
                    if score["development_priority"]<best_loss:
                        best_loss=score["development_priority"]
                        best_state={k:v.detach().cpu().clone()
                                    for k,v in student.state_dict().items()}
                        best_step=step
                    now=time.perf_counter()
                    if now-last_log>=25:
                        print(json.dumps({
                            "mode":label,"seed":seed,"gradient_updates":step,
                            "elapsed_train_seconds":round(now-session_start,1),
                            "best_development_priority":round(best_loss,6)
                        }),flush=True)
                        last_log=now
            elapsed=time.perf_counter()-session_start
            compute_total+=elapsed
            if best_state is None:
                raise ValueError("No development-selected session checkpoint")
            student.load_state_dict(best_state)
            retained=evaluate(student,development)
            ckpt_name=f"{label}__seed_{seed}.safetensors"
            save_file({k:v.detach().cpu().contiguous()
                       for k,v in student.state_dict().items()},
                       archive/ckpt_name)
            detail={
                "seed":seed,"condition":label,
                "session_training_elapsed_seconds":round(elapsed,3),
                "optimizer_updates":step,
                "selected_dev_step":best_step,
                "development_strength_mae":retained["strength_mae"],
                "development_operation_accuracy":retained["accuracy"],
                "development_priority":retained["development_priority"],
                "checkpoint":ckpt_name,
            }
            history[label].append(detail)
            if retained["development_priority"]<winning_priority:
                winning_priority=retained["development_priority"]
                winner={k:v.detach().cpu().clone()
                        for k,v in student.state_dict().items()}
                best_seed=seed
            print("SESSION_COMPLETED "+json.dumps(detail),flush=True)
        model=Student()
        model.load_state_dict(winner)
        winners[label]=model
        history[label+"_winner_seed"]=best_seed
    if compute_total<optimization_seconds:
        raise ValueError("Insufficient measured active CPU training time")

    # Validation must only be loaded/evaluated AFTER all development-only
    # model and seed decisions are frozen.
    blind=tensors("validation")
    heldout={label:evaluate(model,blind) for label,model in winners.items()}
    no=heldout["teacher_free"]
    yes=heldout["DINO_guided"]
    gain=(no["strength_mae"]-yes["strength_mae"])/no["strength_mae"]
    hashes=hashlib.sha256("\n".join(sorted(
        row["original_sha256"] for row in groups["validation"])).encode()).hexdigest()
    provisional=(yes["accuracy"]>=.65 and yes["strength_mae"]<=.18
                 and yes["strength_mae"]<=no["strength_mae"]-.008
                 and yes["accuracy"]>=no["accuracy"]-.03)
    report={
        "schema":EVALUATION_SCHEMA,
        "status":"provisional_strength_pass" if provisional else "research_strength_not_validated",
        "study":"strength_marathon_v3",
        "original_meshes":888,"original_before_after_changes":864,
        "train_examples":672,"development_examples":96,
        "untouched_holdout_examples":96,
        "independent_seeds_per_condition":8,
        "completed_independent_training_sessions":16,
        "requested_active_training_seconds":optimization_seconds,
        "verified_active_training_seconds":round(compute_total,3),
        "training_data":"original verified Kotlin GLB meshes and label-free images",
        "frozen_teacher":"DINOv2 Small auxiliary during training only",
        "teacher_generates_geometry":False,
        "teacher_needed_at_inference":False,
        "source_validation_hashes_sha256":hashes,
        "all_session_development_results":history,
        "heldout":heldout,
        "teacher_strength_gain_fraction":gain,
        "real_native_geometry_reconstruction_completed":False,
        "human_review_required":True,
        "android_deployable":False
    }
    proposal={
        "schema":PROPOSAL_SCHEMA,
        "source_hashes_sha256":hashes,
        "external_mesh_used":False,
        "teacher_free":[],
        "DINO_guided":[]
    }
    for label,model in winners.items():
        model.eval()
        with torch.inference_mode():
            score,heads,_,_=model(blind[0])
            operations=score.argmax(dim=1)
            strengths=heads.gather(1,operations[:,None]).flatten()
        for i,row in enumerate(groups["validation"]):
            proposal[label].append({
                "case":row["case"],
                "source_glb_sha256":row["original_sha256"],
                "baseline_glb_sha256":row["baseline_sha256"],
                "predicted_operation":OPERATIONS[int(operations[i])],
                "predicted_strength":round(float(strengths[i]),7),
                **row["dimensions"]
            })
    candidate={
        "schema":STUDENT_SCHEMA,
        "original_native_generator":"AssetWright-Kotlin-AdvancedFormLab",
        "teacher_needed_at_inference":False,
        "teacher_generates_geometry":False,
        "android_deployable":False,
        "approved_for_generation":False,
        "seed":history["DINO_guided_winner_seed"],
        "input_feature_dim":INPUTS,
        "model_hidden_dim":HIDDEN,
        "supported_ops":list(OPERATIONS),
        "train_feature_mean":means.tolist(),
        "train_feature_std":scales.tolist(),
        "train_morph_std":m_scales.tolist(),
        "frozen_original_weights":{k:v.detach().cpu().tolist()
                                    for k,v in winners["DINO_guided"].state_dict().items()},
        "blind_source_hashes_sha256":hashes,
    }
    (out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"candidate_student.json").write_text(json.dumps(candidate,separators=(",",":"))+"\n")
    (out/"proposals.json").write_text(json.dumps(proposal,indent=2)+"\n")
    lines=["schema="+PROPOSAL_SCHEMA,"external_mesh_used=false","count=96"]
    for label in ("teacher_free","DINO_guided"):
        for i,record in enumerate(proposal[label]):
            for key,value in record.items():
                lines.append(f"{label}.{i}.{key}={value}")
    (out/"native_proposals.properties").write_text("\n".join(lines)+"\n")
    print("FROZEN_BLIND_RESULT "+json.dumps({
        "status":report["status"],
        "trained_seconds":report["verified_active_training_seconds"],
        "control":heldout["teacher_free"],
        "DINO_guided":heldout["DINO_guided"],
        "selected_seeds":{key:history[key+"_winner_seed"]
                          for key in ("teacher_free","DINO_guided")},
        "android_deployed":False
    }),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--teacher",type=Path,required=True)
    p.add_argument("--images",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--training-seconds",type=int,default=1920)
    a=p.parse_args()
    fit(json.loads(a.manifest.read_text()),
        json.loads(a.teacher.read_text()),
        a.images,a.out,a.training_seconds)


if __name__=="__main__":
    main()

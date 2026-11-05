"""Train an ORIGINAL image->native-operator student using frozen DINO teaching.

The *student* reads only source-rendered pixels and outputs one of six real
AssetWright operators plus bounded strength; at inference it uses no DINO.
All claimed improvements use different source geometry families and tests.
Research-only: a prediction is not a production-ready GLB.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

from dino_native_visual_school import (
    MANIFEST_SCHEMA, TEACHER_SCHEMA, MODEL as TEACHER,
    VIEWS, FAMILIES, OPERATIONS, checked_manifest)
from visual_transfer_student import project_teacher

STUDENT="assetwright-owned-image-native-operator-student-v1"
PIXELS_PER_VIEW=12
FEATURE_DIM=2*(2*PIXELS_PER_VIEW**2+2*PIXELS_PER_VIEW)
OUTPUTS=6


def image_features(paths:list[Path])->list[float]:
    """Fixed pooled visual measurements of *pixels*, no source file labels."""
    import numpy as np
    from PIL import Image
    if len(paths)!=len(VIEWS):
        raise ValueError("Missing source camera views")
    out=[]
    for path in paths:
        with Image.open(path) as img:
            rgb=np.asarray(img.convert("RGB").resize(
                (PIXELS_PER_VIEW,PIXELS_PER_VIEW),Image.Resampling.BOX),
                dtype=np.float64)/255.
        # Renderer uses one constant dark gray background. Geometry pixels
        # are observed by intensity difference, never by file name or label.
        brightness=.299*rgb[:,:,0]+.587*rgb[:,:,1]+.114*rgb[:,:,2]
        occupancy=np.clip((brightness-.10)*3.2,0,1)
        out.extend(occupancy.ravel().tolist())
        out.extend(brightness.ravel().tolist())
        out.extend(occupancy.mean(axis=0).tolist())
        out.extend(occupancy.mean(axis=1).tolist())
    if len(out)!=FEATURE_DIM:
        raise AssertionError("Unexpected owned image student feature size")
    return out


def aligned_examples(manifest:dict, teacher:dict, images:Path)->list[dict]:
    rows=checked_manifest(manifest,images)
    if (teacher.get("schema")!=TEACHER_SCHEMA or teacher.get("teacher")!=TEACHER or
            teacher.get("frozen") is not True or
            teacher.get("external_mesh_generator") is not False):
        raise ValueError("Unapproved DINO teacher")
    records=teacher.get("examples")
    if not isinstance(records,list) or len(records)!=len(rows):
        raise ValueError("Incomplete frozen DINO teacher source coverage")
    feature_map={}
    for record in records:
        key=record.get("case")
        if key in feature_map or not isinstance(key,str):
            raise ValueError("Duplicate teacher representation")
        feature_map[key]=record
    samples=[]
    for row in rows:
        target=feature_map.get(row["case"])
        if (target is None or target.get("source_glb_sha256")!=row["source_glb_sha256"] or
                target.get("view_sha256")!=row["view_sha256"]):
            raise ValueError("Source image/GLB/teacher hash mismatch")
        signature=project_teacher(target.get("frozen_visual_embedding"))
        samples.append({"case":row["case"],"split":row["split"],
                        "family":row["family"],"sha":row["source_glb_sha256"],
                        "operation":row["operation"],"strength":row["strength"],
                        "dimensions":{k:row[k] for k in ("length","width","height")},
                        "pixels":image_features([images/row["view_files"][v] for v in VIEWS]),
                        "teacher":signature})
    if len(samples)!=252:
        raise ValueError("Missing native supervised image learning examples")
    return samples


def fit(manifest:dict,teacher:dict,images:Path)->tuple[dict,dict,dict]:
    import numpy as np
    import torch
    from torch import nn
    import torch.nn.functional as F

    samples=aligned_examples(manifest,teacher,images)
    groups={phase:[s for s in samples if s["split"]==phase]
            for phase in ("train","development","validation")}
    if {p:len(r) for p,r in groups.items()}!={"train":180,"development":36,"validation":36}:
        raise ValueError("Invalid source partition counts")
    if any(set(FAMILIES[a])&set(FAMILIES[b]) for a,b in
           (("train","development"),("train","validation"),("development","validation"))):
        raise ValueError("Native source family leakage")
    if len({s["sha"] for s in samples})!=len(samples):
        raise ValueError("Cross-source mesh duplication")
    torch.set_num_threads(min(2,torch.get_num_threads()))
    x_train=np.asarray([r["pixels"] for r in groups["train"]],dtype=np.float32)
    mu=x_train.mean(axis=0)
    # Keep regularized and non-zero for flat pixels (prevent train-only normalization leaks).
    sd=np.maximum(x_train.std(axis=0),.075)
    def tensor_split(phase):
        rows=groups[phase]
        return (torch.tensor((np.asarray([r["pixels"] for r in rows],dtype=np.float32)-mu)/sd),
                torch.tensor([OPERATIONS.index(r["operation"]) for r in rows],dtype=torch.long),
                torch.tensor([[r["strength"]] for r in rows],dtype=torch.float32),
                torch.tensor([r["teacher"] for r in rows],dtype=torch.float32))
    train=tensor_split("train")
    dev=tensor_split("development")
    hold=tensor_split("validation")

    class OriginalStudent(nn.Module):
        def __init__(self):
            super().__init__()
            self.body=nn.Sequential(nn.Linear(FEATURE_DIM,96),nn.Tanh())
            self.operation=nn.Linear(96,OUTPUTS)
            self.strength=nn.Linear(96,1)
            self.visual=nn.Linear(96,24)
        def forward(self,x):
            h=self.body(x)
            return self.operation(h),torch.sigmoid(self.strength(h)),torch.tanh(self.visual(h))

    def metrics(model,partition):
        model.eval()
        xx,cls,strength,_=partition
        with torch.inference_mode():
            logits,power,_=model(xx)
            guess=logits.argmax(dim=1)
            return {"accuracy":float((guess==cls).float().mean()),
                    "strength_mae":float((power-strength).abs().mean()),
                    "operation_ce":float(F.cross_entropy(logits,cls)),
                    "joint":float(F.cross_entropy(logits,cls)+2.*(power-strength).abs().mean())}
    def train_student(use_teacher):
        torch.manual_seed(20261104)
        model=OriginalStudent()
        optimizer=torch.optim.Adam(model.parameters(),lr=.004,weight_decay=.0003)
        best=None;best_score=float("inf");best_epoch=0
        xx,cls,strength,feature=train
        for epoch in range(260):
            model.train()
            op,power,vision=model(xx)
            loss=(F.cross_entropy(op,cls)+2.0*F.smooth_l1_loss(power,strength))
            if use_teacher:
                loss=loss+.75*F.mse_loss(vision,feature)
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),2.)
            optimizer.step()
            if (epoch+1)%5==0:
                score=metrics(model,dev)["joint"]
                if score<best_score:
                    best_score=score
                    best=copy.deepcopy(model.state_dict())
                    best_epoch=epoch+1
        if best is None:
            raise ValueError("No development-selected owned student weights")
        model.load_state_dict(best)
        return model,{"best_development_joint":round(best_score,7),
                      "development_chosen_epoch":best_epoch}

    pure,baseline_dev=train_student(False)
    distilled,teacher_dev=train_student(True)
    baseline=metrics(pure,hold)
    taught=metrics(distilled,hold)
    test=groups["validation"]
    # Do not select or tune on final untouched validation; compare frozen pair once.
    gains={"joint_fraction":(baseline["joint"]-taught["joint"])/baseline["joint"],
           "accuracy_points":taught["accuracy"]-baseline["accuracy"],
           "strength_mae_delta":baseline["strength_mae"]-taught["strength_mae"]}
    naive_strength=float(np.mean([r["strength"] for r in groups["train"]]))
    op_counts=Counter(r["operation"] for r in groups["train"])
    majority=max(OPERATIONS,key=lambda k:op_counts[k])
    naive_correct=sum(r["operation"]==majority for r in test)/len(test)
    naive_power=sum(abs(r["strength"]-naive_strength) for r in test)/len(test)
    # Research gate is strict: frozen teacher must improve on native-task
    # baselines and maintain plausible operator/continuous-strength recovery.
    passed=(taught["accuracy"]>=.55 and taught["strength_mae"]<=.20 and
            gains["joint_fraction"]>=.03 and
            taught["accuracy"]+1e-6>=baseline["accuracy"]-.03 and
            taught["strength_mae"]<=baseline["strength_mae"]+.02)
    report={
        "schema":"assetwright-original-geometry-dino-visual-study-v1",
        "status":"validated_research_visual_to_native" if passed else "rejected_visual_teacher_transfer",
        "source":"252 original Kotlin AdvancedFormLab GLBs with independent manifold/topology audits",
        "train_native_glbs":180,"development_native_glbs":36,
        "official_unseen_native_glbs":36,
        "source_view_count":len(VIEWS),
        "teacher":"frozen "+TEACHER,
        "teacher_generates_3d":False,
        "pixel_student_requires_teacher_at_inference":False,
        "teacher_free_baseline":baseline,
        "teacher_distilled_student":taught,
        "evaluation_improvement":{k:round(v,6) for k,v in gains.items()},
        "uninformed_operation_accuracy":naive_correct,
        "uninformed_strength_mae":naive_power,
        "baseline_development":baseline_dev,
        "distilled_development":teacher_dev,
        "heldout_source_sha256":hashlib.sha256(
            "\n".join(sorted(x["sha"] for x in test)).encode()).hexdigest(),
        "actual_target_glbs_structurally_audited":True,
        "predicted_native_glbs_reconstructed":False,
        "human_visual_approval":False,
        "android_deployed":False,
        "note":"Predicts six existing native construction controls from source-rendered pixels, not arbitrary open-domain CAD or automotive design."
    }
    model_package={
        "schema":STUDENT,"generator_authority":"AssetWright-Kotlin-AdvancedFormLab",
        "inference":"original_pixel_features_only",
        "input_dimensions":FEATURE_DIM,"supported_native_operations":list(OPERATIONS),
        "input_mean":mu.tolist(),"input_std":sd.tolist(),
        "weights":{k:v.detach().cpu().tolist() for k,v in distilled.state_dict().items()},
        "teacher_runtime_required":False,"android_deployable":False,
        "approved_for_geometry_generation":False,
        "validated_visual_transfer":passed
    }
    distilled.eval()
    with torch.inference_mode():
        op,power,_=distilled(hold[0])
    predictions=[]
    for index,row in enumerate(test):
        predictions.append({
            "case":row["case"],"source_glb_sha256":row["sha"],
            "family":row["family"],"source_operation":row["operation"],
            "target_strength":row["strength"],
            "predicted_operation":OPERATIONS[int(op[index].argmax())],
            "predicted_strength":round(float(power[index].item()),6),
            "length":row["dimensions"]["length"],
            "width":row["dimensions"]["width"],
            "height":row["dimensions"]["height"],
        })
    proposals={"schema":"assetwright-own-dino-native-proposals-v1",
               "research_only":True,"original_mesh_generator":"AssetWright-AdvancedFormLab",
               "teacher_used_at_inference":False,
               "samples":predictions}
    return report,model_package,proposals


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--teacher",required=True,type=Path)
    p.add_argument("--images",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    report,package,proposals=fit(json.loads(a.manifest.read_text()),
                                 json.loads(a.teacher.read_text()),a.images)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (a.out/"candidate_pixel_student.json").write_text(json.dumps(package)+"\n")
    (a.out/"candidate_native_proposals.json").write_text(json.dumps(proposals,indent=2)+"\n")
    (a.out/"validated_research_student.json").unlink(missing_ok=True)
    if report["status"]=="validated_research_visual_to_native":
        (a.out/"validated_research_student.json").write_text(json.dumps(package)+"\n")
    print(json.dumps(report,indent=2))
    # An honest negative research result is an evaluated experiment, not a
    # pipeline failure. Source/split/provenance errors still fail the CI.


if __name__=="__main__":
    main()

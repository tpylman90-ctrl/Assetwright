"""Original before/after image student learns native operation and strength.

Teacher-free after-only and paired comparisons are trained alongside the
frozen DINO-delta-supervised student. At inference only image pixels are read;
all GLBs used for ground truth are original AssetWright Kotlin geometry.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path

from advanced_form_student import OPERATIONS
from dino_delta_school import (DINO,TEACHER, VIEWS, FAMILIES,
                               checked_manifest)
from visual_transfer_student import project_teacher

SCHEMA="assetwright-original-before-after-native-student-v1"
GRID=16
INPUT_DIM=2*3*GRID*GRID
HIDDEN=128


def image_features(row:dict,images:Path,*,after_only:bool=False)->list[float]:
    """Fixed label-free 16x16 pixel silhouettes/deltas from shared cameras."""
    import numpy as np
    from PIL import Image
    result=[]
    for view in VIEWS:
        with Image.open(images/row["before_view_files"][view]) as im:
            before=np.asarray(im.convert("RGB").resize(
                (GRID,GRID),Image.Resampling.BOX),dtype=np.float32)/255.
        with Image.open(images/row["after_view_files"][view]) as im:
            after=np.asarray(im.convert("RGB").resize(
                (GRID,GRID),Image.Resampling.BOX),dtype=np.float32)/255.
        def bands(x):
            gray=.299*x[:,:,0]+.587*x[:,:,1]+.114*x[:,:,2]
            occupancy=np.clip((gray-.10)*3.2,0,1)
            return gray,occupancy
        a,occ_a=bands(before)
        b,occ_b=bands(after)
        delta=occ_b-occ_a
        gray_delta=b-a
        if after_only:
            delta=np.zeros_like(delta)
            gray_delta=np.zeros_like(gray_delta)
        result.extend(occ_b.ravel().tolist())
        result.extend(delta.ravel().tolist())
        result.extend(gray_delta.ravel().tolist())
    if len(result)!=INPUT_DIM: raise AssertionError("Unexpected image student dimension")
    return result


def align(manifest:dict,teacher:dict,images:Path)->list[dict]:
    records=checked_manifest(manifest,images)
    if (teacher.get("schema")!=TEACHER or teacher.get("teacher")!=DINO or
        teacher.get("teacher_frozen") is not True or
        teacher.get("teacher_generates_3d") is not False):
        raise ValueError("Unapproved DINOv2 frozen transformation teacher")
    lessons=teacher.get("examples")
    if not isinstance(lessons,list) or len(lessons)!=len(records):
        raise ValueError("Missing frozen before/after teacher lessons")
    lookup={}
    for item in lessons:
        case=item.get("case")
        if not isinstance(case,str) or case in lookup:
            raise ValueError("Duplicate or invalid teacher lesson")
        lookup[case]=item
    rows=[];changed_hashes=set()
    for item in records:
        t=lookup.get(item["case"])
        if (t is None or
            t.get("baseline_glb_sha256")!=item["baseline_glb_sha256"] or
            t.get("modified_glb_sha256")!=item["modified_glb_sha256"] or
            t.get("before_view_sha256")!=item["before_view_sha256"] or
            t.get("after_view_sha256")!=item["after_view_sha256"]):
            raise ValueError("Teacher and original mesh/image delta provenance mismatch")
        signature=t.get("frozen_dino_delta_signature")
        if not isinstance(signature,list) or len(signature)!=24 or any(
            type(v) not in (int,float) or not -1.1<=v<=1.1 for v in signature):
            raise ValueError("Untrusted frozen DINO delta signature")
        if item["modified_glb_sha256"] in changed_hashes:
            raise ValueError("Repeated native target geometry")
        changed_hashes.add(item["modified_glb_sha256"])
        rows.append({
            "case":item["case"],"split":item["split"],"family":item["family"],
            "operation":item["operation"],"strength":item["strength"],
            "baseline_hash":item["baseline_glb_sha256"],
            "source_hash":item["modified_glb_sha256"],
            "dimensions":{k:item[k] for k in ("length","width","height")},
            "pixels":image_features(item,images),
            "after_only_pixels":image_features(item,images,after_only=True),
            "morphology_delta":item["measured_morphology_delta"],
            "dino_delta":signature
        })
    if len(rows)!=468:
        raise ValueError("Missing native before/after records")
    return rows


def fit(manifest:dict,teacher:dict,images:Path)->tuple[dict,dict,dict,dict]:
    import numpy as np
    import torch
    from torch import nn
    import torch.nn.functional as F

    rows=align(manifest,teacher,images)
    partitions={name:[r for r in rows if r["split"]==name]
                for name in ("train","development","validation")}
    if {name:len(x) for name,x in partitions.items()}!={
        "train":360,"development":54,"validation":54}:
        raise ValueError("Invalid family-disjoint source partition counts")
    if any(set(FAMILIES[a])&set(FAMILIES[b]) for a,b in
           (("train","development"),("train","validation"),("development","validation"))):
        raise ValueError("Leaked original native shape families")
    torch.set_num_threads(min(2,torch.get_num_threads()))
    training=partitions["train"]
    pixel_mu=np.asarray([r["pixels"] for r in training],dtype=np.float32).mean(axis=0)
    pixel_sd=np.maximum(np.asarray([r["pixels"] for r in training],dtype=np.float32).std(axis=0),.065)
    morph=np.asarray([r["morphology_delta"] for r in training],dtype=np.float32)
    morph_scale=np.maximum(morph.std(axis=0),.075)
    def data(phase,*,after_only=False):
        batch=partitions[phase]
        key="after_only_pixels" if after_only else "pixels"
        x=(np.asarray([r[key] for r in batch],dtype=np.float32)-pixel_mu)/pixel_sd
        return (
            torch.tensor(x,dtype=torch.float32),
            torch.tensor([OPERATIONS.index(r["operation"]) for r in batch],dtype=torch.long),
            torch.tensor([[r["strength"]] for r in batch],dtype=torch.float32),
            torch.tensor(np.asarray([r["morphology_delta"] for r in batch],dtype=np.float32)/morph_scale),
            torch.tensor([r["dino_delta"] for r in batch],dtype=torch.float32)
        )
    full_train=data("train")
    full_dev=data("development")
    full_test=data("validation")
    after_train=data("train",after_only=True)
    after_dev=data("development",after_only=True)
    after_test=data("validation",after_only=True)

    class OurStudent(nn.Module):
        def __init__(self):
            super().__init__()
            self.body=nn.Sequential(nn.Linear(INPUT_DIM,HIDDEN),nn.Tanh())
            self.operation=nn.Linear(HIDDEN,len(OPERATIONS))
            self.strength=nn.Linear(HIDDEN,1)
            self.geometry=nn.Linear(HIDDEN,6)
            self.vision=nn.Linear(HIDDEN,24)
        def forward(self,x):
            z=self.body(x)
            return (self.operation(z),torch.sigmoid(self.strength(z)),
                    self.geometry(z),self.vision(z))

    def score(model,batch):
        model.eval()
        x,operations,strength,_,_=batch
        with torch.inference_mode():
            logits,predicted,_,_=model(x)
            classes=logits.argmax(dim=1)
            ce=float(F.cross_entropy(logits,operations))
            mae=float((predicted-strength).abs().mean())
            per_class={
                op:{"correct":int(((classes==i)&(operations==i)).sum()),
                    "total":int((operations==i).sum())}
                for i,op in enumerate(OPERATIONS)
            }
            return {"accuracy":float((classes==operations).float().mean()),
                    "strength_mae":mae,"operation_ce":ce,
                    "joint":ce+2*mae,"per_class":per_class}

    def train_student(name,train_data,dev_data,*,dino:bool):
        torch.manual_seed(20261105)
        model=OurStudent()
        optim=torch.optim.AdamW(model.parameters(),lr=.003,weight_decay=.001)
        inputs,operation,strength,morphology,vision=train_data
        best=None;best_loss=float("inf");best_epoch=0
        for epoch in range(360):
            model.train()
            op,power,shape,features=model(inputs)
            loss=F.cross_entropy(op,operation)+1.3*F.l1_loss(power,strength)
            loss=loss+.22*F.smooth_l1_loss(shape,morphology)
            if dino:
                loss=loss+.65*F.mse_loss(features,vision)
            optim.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),2.)
            optim.step()
            if (epoch+1)%5==0:
                dev_metrics=score(model,dev_data)
                if dev_metrics["joint"]<best_loss:
                    best_loss=dev_metrics["joint"]
                    best=copy.deepcopy(model.state_dict())
                    best_epoch=epoch+1
        if best is None:
            raise ValueError("No trained model selected on disjoint development")
        model.load_state_dict(best)
        return model,{"selected_development_epoch":best_epoch,
                      "development_joint":round(best_loss,8),
                      "mode":name}

    after,after_history=train_student("after_only",after_train,after_dev,dino=False)
    paired,paired_history=train_student("paired_with_morphology",full_train,full_dev,dino=False)
    guided,guided_history=train_student("paired_morphology_plus_frozen_DINO",full_train,full_dev,dino=True)

    # Score exactly once on untouched source-family validation, no selection.
    results={"after_only":score(after,after_test),
             "paired_without_DINO":score(paired,full_test),
             "paired_with_DINO":score(guided,full_test)}
    base=results["after_only"]
    no_dino=results["paired_without_DINO"]
    yes_dino=results["paired_with_DINO"]
    pair_gain=(base["joint"]-no_dino["joint"])/base["joint"]
    dino_gain=(no_dino["joint"]-yes_dino["joint"])/no_dino["joint"]
    accepted=(yes_dino["accuracy"]>=.60 and yes_dino["strength_mae"]<=.18
              and pair_gain>=.05 and dino_gain>=.025
              and yes_dino["accuracy"]+1.e-6>=no_dino["accuracy"]-.02
              and yes_dino["strength_mae"]<=no_dino["strength_mae"]+.015)
    source_hash=hashlib.sha256("\n".join(sorted(
        r["source_hash"] for r in partitions["validation"])).encode()).hexdigest()
    report={
        "schema":"assetwright-native-before-after-visual-comparison-v1",
        "status":"provisional_visual_transfer_pass" if accepted else "visual_transfer_not_yet_validated",
        "original_kotlin_glbs":486,"native_before_after_pairs":468,
        "train_examples":360,"development_examples":54,
        "fresh_validation_examples":54,
        "source_family_disjoint":True,
        "camera_alignment":"identical per native source family",
        "vision_teacher":"frozen "+DINO,
        "external_AI_generates_3d":False,
        "model_inference_requires_DINO":False,
        "metrics":results,
        "before_after_joint_improvement_fraction":round(pair_gain,6),
        "DINO_joint_improvement_vs_paired":round(dino_gain,6),
        "training_procedure":{
            "same_architecture_and_seed":True,
            "selected_using":"disjoint_development_only",
            "after_only":after_history,
            "pair_no_teacher":paired_history,
            "pair_frozen_dino_teacher":guided_history
        },
        "heldout_modified_source_hashes_sha256":source_hash,
        "predicted_original_geometry_reconstructed":False,
        "android_deployable":False,
        "approved_for_geometry_generation":False,
        "note":"Small original procedural surface-operation family benchmark. Visual scoring alone cannot approve native geometry."
    }

    def predictions(model):
        model.eval()
        with torch.inference_mode():
            op,power,_,_=model(full_test[0])
        proposals=[]
        for i,row in enumerate(partitions["validation"]):
            proposals.append({
                "case":row["case"],"source_glb_sha256":row["source_hash"],
                "baseline_glb_sha256":row["baseline_hash"],
                "predicted_operation":OPERATIONS[int(op[i].argmax())],
                "predicted_strength":round(float(power[i]),7),
                **row["dimensions"]
            })
        return proposals
    proposals={
        "schema":"assetwright-native-before-after-proposals-v1",
        "external_AI_meshes_used":False,
        "source_modified_hashes_sha256":source_hash,
        "teacher_free":predictions(paired),
        "DINO_guided":predictions(guided)
    }
    package={
        "schema":SCHEMA,"generator_authority":"AssetWright-Kotlin-AdvancedFormLab",
        "input":"two_before_after_render_views_with_no_labels",
        "input_dim":INPUT_DIM,"hidden_dim":HIDDEN,"operations":list(OPERATIONS),
        "train_pixel_mean":pixel_mu.tolist(),"train_pixel_std":pixel_sd.tolist(),
        "train_morphology_scale":morph_scale.tolist(),
        "weights":{k:v.detach().cpu().tolist() for k,v in guided.state_dict().items()},
        "teacher":"frozen_DINOv2_training_only",
        "teacher_required_at_inference":False,
        "provisional_visual_pass":accepted,
        "approved_for_geometry_generation":False,"android_deployable":False
    }
    return report,package,proposals,{"paired_only":{
        k:v.detach().cpu().tolist() for k,v in paired.state_dict().items()}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("manifest","teacher","images","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    a=parser.parse_args()
    report,package,proposals,baseline=fit(
        json.loads(a.manifest.read_text()),json.loads(a.teacher.read_text()),a.images)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (a.out/"candidate_student.json").write_text(json.dumps(package)+"\n")
    (a.out/"baseline_weights.json").write_text(json.dumps(baseline)+"\n")
    (a.out/"reconstruction_proposals.json").write_text(json.dumps(proposals,indent=2)+"\n")
    lines=["schema=assetwright-native-before-after-proposals-v1",
           "external_mesh_used=false","count=54"]
    for variant in ("teacher_free","DINO_guided"):
        for i,record in enumerate(proposals[variant]):
            for key,value in record.items():
                lines.append(f"{variant}.{i}.{key}={value}")
    (a.out/"native_proposals.properties").write_text("\n".join(lines)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="metrics"},indent=2))
    print(json.dumps({"validation_metrics":report["metrics"]},indent=2))

if __name__=="__main__":
    main()

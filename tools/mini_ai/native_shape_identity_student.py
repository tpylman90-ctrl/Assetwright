"""Forge Mini v7: learn SHAPE IDENTITY independently of native actions.

The v6 research form student is SHA256-verified, then completely FROZEN:
all previous operation, strength and morphology parameters are immutable.
Only a NEW 3-view 32x32 shape identity encoder learns. The original v6
student is an EXPERIMENTAL parent (v6 promotion failed); production v3
knowledge remains unchanged.

The identity labels come from 56 DISTINCT original source baselines:
40 NEW v7 forms counterbalanced for dimensions, plus 16 v6 TRAIN-only
forms. The 1,200 original v7 transform pairs validate the form geometry,
but their same-baseline 3-view descriptor is NOT counted as 1,200
independent identity examples.

Two per-form NEW dev families and two per-form fresh BLIND families
never participate in gradient updates. All 384 blind transform targets
are inspected just once AFTER condition and checkpoint selection.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time

from advanced_form_student import OPERATIONS
from dino_delta_student import image_features,INPUT_DIM as OLD_INPUT
from dino_delta_school import STUDY,FAMILIES,LEVELS,checked_manifest
from native_multiform_student import FORMS
from native_shape_identity_views import (
    SCHEMA as VIEW_SCHEMA,INPUT_DIM as ID_INPUT,features)

CONDITIONS=("three_view","contrastive_identity","hard_form_distinctions")
SEEDS=(313,1601)
VARIANTS=("prior",)+CONDITIONS
SCHEMA="assetwright-original-shape-identity-training-v7"
MODEL_SCHEMA="assetwright-original-shape-identity-lineage-v7"
PROPOSAL_SCHEMA="assetwright-original-v7-form-predictions-v1"


def digest(file:Path)->str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def unique_source_rows(manifest:dict,images:Path,extra:Path,
                       *,study:str,splits:tuple)->list[dict]:
    if (manifest.get("schema")!="assetwright-native-before-after-observations-v1"
        or manifest.get("study_id")!=study
        or manifest.get("external_geometry_used") is not False):
        raise ValueError("Unknown own original three-view geometry source")
    index=json.loads((extra/"index.json").read_text())
    if (index.get("schema")!=VIEW_SCHEMA
        or index.get("study_id")!=study
        or index.get("input_only_original_baseline") is not True):
        raise ValueError("Geometry identity index source not original")
    rows={}
    for record in manifest["records"]:
        if record["split"] not in splits:
            continue
        key=(record["split"],record["family"])
        if key in rows:continue
        if record.get("archetype") not in FORMS[1:]:
            raise ValueError("Unknown original form archetype")
        rows[key]={
            "split":record["split"],"family":record["family"],
            "form":record["archetype"],"form_id":FORMS.index(record["archetype"]),
            "identity":features(record,images,extra,index),
            "baseline_sha":record["baseline_glb_sha256"],
            "baseline_case":record["baseline_case"],
            # prior original student's unchanged, label-free image input
            "old_image":image_features(record,images)
        }
    expected=(16 if study=="multiform_v6" else
              sum(len(FAMILIES[s]) for s in splits))
    if len(rows)!=expected:
        raise ValueError("Shape identity families not original / disjoint")
    if len({v["baseline_sha"] for v in rows.values()})!=len(rows):
        raise ValueError("Repeated original shape in independent families")
    for split in splits:
        items=[r for r in rows.values() if r["split"]==split]
        total=len(items)
        if total%8 or {form:sum(x["form"]==form for x in items)
            for form in FORMS[1:]}.values()!={total//8}:
            raise ValueError("Form dataset not counterbalanced")
    return list(rows.values())


def train(new_manifest:Path,new_images:Path,new_views:Path,
          legacy_manifest:Path,legacy_images:Path,legacy_views:Path,
          old_knowledge:Path,output:Path,active_seconds:int):
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from safetensors.torch import load_file,save_file
    if STUDY!="shape_identity_v7":
        raise ValueError("Fresh v7 form identity study not selected")
    if not 1200<=active_seconds<=2100:
        raise ValueError("New shape training needs 20–35 CPU gradient minutes")
    source=json.loads(new_manifest.read_text())
    checked_manifest(source,new_images)  # all images/hashes, never train on blind
    prior=json.loads(legacy_manifest.read_text())
    old_rows=unique_source_rows(
        prior,legacy_images,legacy_views,
        study="multiform_v6",splits=("train",))
    rows=unique_source_rows(
        source,new_images,new_views,study="shape_identity_v7",
        splits=("train","development","validation"))
    new_train=[r for r in rows if r["split"]=="train"]
    dev=[r for r in rows if r["split"]=="development"]
    blind=[r for r in rows if r["split"]=="validation"]
    if tuple(map(len,(old_rows,new_train,dev,blind)))!=(16,40,16,16):
        raise ValueError("Incorrect genuinely independent native shape families")
    # Check exact original v6 weights but never call them approved for mobile.
    history=json.loads((old_knowledge/"learning_history.json").read_text())
    lineage=json.loads((old_knowledge/"lineage.json").read_text())
    path=old_knowledge/"balanced_forms.safetensors"
    if (history.get("research_gate")!="research_not_promoted_legacy_checkpoint_retained"
        or history["candidate_weight_sha256"]["balanced_forms"]!=digest(path)
        or lineage["schema"]!="assetwright-original-8-archetype-neural-weights-v6"
        or len(lineage["pixel_mean"])!=OLD_INPUT
        or len(lineage["pixel_std"])!=OLD_INPUT
        or len(lineage["form_names"])!=9):
        raise ValueError("Experimental original v6 parent checkpoint changed")
    old_mean=np.asarray(lineage["pixel_mean"],dtype=np.float32)
    old_std=np.asarray(lineage["pixel_std"],dtype=np.float32)

    class Parent(nn.Module):
        def __init__(self):
            super().__init__()
            self.core=nn.Sequential(
                nn.Linear(OLD_INPUT,96),nn.Tanh(),
                nn.Linear(96,96),nn.Tanh())
            self.op=nn.Linear(96,len(OPERATIONS))
            self.strength=nn.Linear(96,len(OPERATIONS))
            self.physical=nn.Linear(96,6)
            self.dino=nn.Linear(96,24)
            self.form=nn.Linear(96,len(FORMS))
        def forward(self,x):
            h=self.core(x)
            return self.op(h),torch.sigmoid(self.strength(h)),self.form(h)

    class Identity(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder=nn.Sequential(
                nn.Linear(ID_INPUT,128),nn.GELU(),
                nn.Linear(128,96),nn.GELU())
            self.classifier=nn.Linear(96,len(FORMS))
        def forward(self,x):
            h=self.encoder(x)
            return self.classifier(h),h

    torch.set_num_threads(min(2,torch.get_num_threads()))
    parent=Parent()
    parent.load_state_dict(load_file(str(path),device="cpu"),strict=True)
    parent.eval()
    for p in parent.parameters():p.requires_grad_(False)
    all_train=old_rows+new_train
    originals=np.asarray([r["identity"] for r in all_train],dtype=np.float32)
    identity_mean=originals.mean(0)
    identity_std=np.maximum(originals.std(0),.08)
    def tensors(rows):
        identity=np.asarray([r["identity"] for r in rows],dtype=np.float32)
        prior_x=np.asarray([r["old_image"] for r in rows],dtype=np.float32)
        return (
            torch.from_numpy((identity-identity_mean)/identity_std),
            torch.from_numpy((prior_x-old_mean)/old_std),
            torch.tensor([r["form_id"] for r in rows],dtype=torch.long)
        )
    training=tensors(all_train)
    developing=tensors(dev)
    old_training=tensors(old_rows)
    assert len(all_train)==56
    with torch.no_grad():
        parent_train=parent(training[1])[2]
        parent_dev=parent(developing[1])[2]
        old_logits=parent(old_training[1])[2]
    # All form classes equally represented among unique SOURCE shapes.
    indices_by_form=[
        torch.tensor([i for i,r in enumerate(all_train)
                      if r["form_id"]==k],dtype=torch.long)
        for k in range(1,9)
    ]
    if any(len(q)!=7 for q in indices_by_form):
        raise ValueError("All eight original form types must have seven TRAIN examples")
    def metrics(model,data,parent_scores):
        model.eval()
        with torch.no_grad():
            inferred,_=model(data[0])
            logits=inferred+.18*parent_scores
            predicted=logits.argmax(1)
            labels=data[2]
            correct=predicted.eq(labels)
            accuracy=float(correct.float().mean())
            per={FORMS[k]:{
                "count":int(labels.eq(k).sum()),
                "correct":int((labels.eq(k)&correct).sum())
            } for k in range(1,9)}
            weak=sum(x["correct"]==0 for x in per.values())
            return {
                "accuracy":accuracy,
                "cross_entropy":float(F.cross_entropy(logits,labels)),
                "predicted_form_count":len(set(predicted.tolist())-{0}),
                "legacy_shell_predictions":int(predicted.eq(0).sum()),
                "weak_form_count":weak,
                "per_form":per,
                "selection_priority":float(
                    F.cross_entropy(logits,labels))+1.2*(1-accuracy)+.15*weak
            }
    def contrastive(h,labels):
        normalized=F.normalize(h,dim=1)
        sim=(normalized@normalized.T)/.20
        diagonal=torch.eye(len(labels),dtype=torch.bool)
        sim=sim.masked_fill(diagonal,-1e4)
        positive=(labels[:,None]==labels[None,:])&~diagonal
        log_probability=sim-torch.logsumexp(sim,dim=1,keepdim=True)
        return -((log_probability*positive).sum(1)/
                 positive.sum(1).clamp_min(1)).mean()

    output.mkdir(parents=True,exist_ok=True)
    (output/"sessions").mkdir(exist_ok=True)
    (output/"winners").mkdir(exist_ok=True)
    duration=active_seconds/(len(CONDITIONS)*len(SEEDS))
    reports=[]
    winners={}
    selection={}
    accumulated=0.
    for condition in CONDITIONS:
        chosen_state=None;chosen_info=None;best=float("inf")
        for seed in SEEDS:
            torch.manual_seed(seed)
            model=Identity()
            optimizer=torch.optim.AdamW(model.parameters(),
                                        lr=.00050,weight_decay=.002)
            session_best=float("inf")
            session_weights=None
            session_step=0;step=0
            start=time.perf_counter();last=start
            while time.perf_counter()-start<duration or step<100:
                # Two or more same-class original baselines guaranteed in
                # each batch for contrastive loss, not duplicated transforms.
                if condition=="hard_form_distinctions":
                    sampled=[]
                    for k,candidates in enumerate(indices_by_form,1):
                        count=7 if FORMS[k] in (
                            "BARREL","BOX_MODULE","BLADE","SPINDLE","WEDGE"
                        ) else 4
                        sampled.append(candidates[
                            torch.randint(len(candidates),(count,))])
                    ix=torch.cat(sampled)
                else:
                    ix=torch.cat([x[torch.randint(len(x),(5,))]
                                  for x in indices_by_form])
                batch=training[0][ix]
                # Gentle original-camera exposure augmentation.
                batch=batch+.022*torch.randn_like(batch)
                logits,h=model(batch)
                logits=logits+.18*parent_train[ix]
                label=training[2][ix]
                loss=F.cross_entropy(logits,label)
                if condition=="contrastive_identity":
                    loss+=.16*contrastive(h,label)
                if condition=="hard_form_distinctions":
                    hard=torch.tensor([
                        1.8 if FORMS[int(x)] in (
                            "BARREL","BOX_MODULE","BLADE") else 1.
                        for x in label],dtype=torch.float32)
                    loss+=(hard*F.cross_entropy(
                        logits,label,reduction="none")).mean()*.45
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(),2.)
                optimizer.step()
                step+=1
                if step%80==0:
                    fresh=metrics(model,developing,parent_dev)
                    older=metrics(model,old_training,old_logits)
                    # Old v6 original form understanding cannot be erased.
                    retained=older["accuracy"]>=.80
                    # Do not choose based on the untouched blind families.
                    if retained and fresh["selection_priority"]<session_best:
                        session_best=fresh["selection_priority"]
                        session_weights={
                            k:v.detach().cpu().clone()
                            for k,v in model.state_dict().items()}
                        session_step=step
                    now=time.perf_counter()
                    if now-last>28:
                        print("IDENTITY_OPT "+json.dumps({
                            "condition":condition,"seed":seed,
                            "active_seconds":round(now-start,1),
                            "updates":step,
                            "fresh_dev_accuracy":fresh["accuracy"],
                            "distinct_dev_forms":fresh["predicted_form_count"],
                            "old_v6_form_retained":retained
                        }),flush=True)
                        last=now
            elapsed=time.perf_counter()-start
            accumulated+=elapsed
            if session_weights is None:
                # Preserve honest failure; do not silently substitute random.
                raise ValueError("No original identity checkpoint retained old forms")
            model.load_state_dict(session_weights,strict=True)
            dev_result=metrics(model,developing,parent_dev)
            old_result=metrics(model,old_training,old_logits)
            report={
                "condition":condition,"seed":seed,
                "actual_gradient_seconds":round(elapsed,3),
                "updates":step,"selected_development_step":session_step,
                "development":dev_result,"old_training_retention":old_result
            }
            reports.append(report)
            save_file({k:v.detach().cpu().contiguous()
                       for k,v in model.state_dict().items()},
                      output/"sessions"/(condition+"__"+str(seed)+".safetensors"))
            if dev_result["selection_priority"]<best:
                best=dev_result["selection_priority"]
                chosen_state=copy.deepcopy(session_weights)
                chosen_info={"seed":seed,"step":session_step}
            print("IDENTITY_SESSION_DONE "+json.dumps({
                "condition":condition,"seed":seed,"seconds":elapsed,
                "development_score":dev_result["selection_priority"],
                "old_form_accuracy":old_result["accuracy"]
            }),flush=True)
        selected=Identity()
        selected.load_state_dict(chosen_state,strict=True)
        winners[condition]=selected
        selection[condition]=chosen_info
        save_file({k:v.detach().cpu().contiguous()
                   for k,v in selected.state_dict().items()},
                  output/"winners"/(condition+".safetensors"))
    if accumulated<active_seconds:
        raise ValueError("Configured real CPU optimizer time not reached")
    development={k:metrics(model,developing,parent_dev)
                 for k,model in winners.items()}
    selected_method=min(CONDITIONS,
        key=lambda mode:development[mode]["selection_priority"])

    # Only NOW load blind images. No hyperparameter/epoch/recipe can use them.
    frozen_rows=[r for r in rows if r["split"]=="validation"]
    if len(frozen_rows)!=16:
        raise ValueError("Independent blind source shapes missing")
    valid_source=[r for r in source["records"] if r["split"]=="validation"]
    if len(valid_source)!=384:
        raise ValueError("Full blind native operation/strength tasks missing")
    keyed={r["family"]:r for r in frozen_rows}
    # Form probability is inferred from the originally unmodified shape.
    blind_data=tensors(frozen_rows)
    all_models={"prior":None,**winners}
    proposal={
        "schema":PROPOSAL_SCHEMA,"study":"shape_identity_v7",
        "external_mesh_used":False,"count":len(valid_source),
        **{name:[] for name in VARIANTS}
    }
    blind_metrics={}
    for variant,network in all_models.items():
        predictions={}
        for row in frozen_rows:
            family=row["family"]
            index=frozen_rows.index(row)
            if network is None:
                with torch.no_grad():
                    pred=parent(blind_data[1][index:index+1])[2].argmax(1).item()
            else:
                with torch.no_grad():
                    raw,_=network(blind_data[0][index:index+1])
                    prior_form=parent(blind_data[1][index:index+1])[2]
                    pred=(raw+.18*prior_form).argmax(1).item()
            predictions[family]=FORMS[pred]
        blind_metrics[variant]={
            "source_form_accuracy":sum(
                predictions[r["family"]]==r["form"] for r in frozen_rows)/16,
            "predicted_unique_form_types":len(set(predictions.values())-{"LEGACY_SHELL"}),
            "per_form":{
                form:{
                    "count":2,
                    "correct":sum(predictions[r["family"]]==form
                                  for r in frozen_rows if r["form"]==form)
                } for form in FORMS[1:]
            }
        }
        for row in valid_source:
            # Frozen action/strength model is used for ALL variants.
            p=np.asarray(image_features(row,new_images),dtype=np.float32)
            with torch.no_grad():
                x=torch.tensor((p-old_mean)/old_std).reshape(1,-1)
                logits,heads,_=parent(x)
                op=int(logits.argmax(1).item())
                power=float(heads[0,op].item())
            proposal[variant].append({
                "case":row["case"],
                "source_glb_sha256":row["modified_glb_sha256"],
                "baseline_glb_sha256":row["baseline_glb_sha256"],
                "predicted_operation":OPERATIONS[op],
                "predicted_strength":round(power,7),
                "predicted_archetype":predictions[row["family"]],
                **{k:row[k] for k in ("length","width","height")}
            })
    heldout_sha=hashlib.sha256("\n".join(sorted(
        row["modified_glb_sha256"] for row in valid_source)).encode()).hexdigest()
    report={
        "schema":SCHEMA,"study":"shape_identity_v7",
        "original_v6_experimental_parent_sha256":digest(path),
        "old_model_research_gate":history["research_gate"],
        "original_operation_and_strength_weights_frozen":True,
        "training_unique_native_form_baselines":56,
        "new_training_unique_form_baselines":40,
        "previous_training_only_unique_form_baselines":16,
        "previous_v6_blind_used_in_training":False,
        "fresh_dev_unique_native_forms":16,
        "fresh_blind_unique_native_forms":16,
        "fresh_blind_new_native_transformations":384,
        "balanced_dimensions_across_all_eight_forms":True,
        "separate_32x32_baseline_three_view_encoder":True,
        "same_start_data_budget_all_conditions":True,
        "optimizer_active_seconds":round(accumulated,3),
        "required_seconds":active_seconds,
        "completed_independent_sessions":len(reports),
        "sessions":reports,
        "development":development,
        "development_only_method_selected":selected_method,
        "development_checkpoint_choices":selection,
        "new_blind_source_sha256":heldout_sha,
        "new_blind_form_results":blind_metrics,
        "native_real_GLBS_to_verify":384*len(VARIANTS),
        "no_pretrained_outside_AI":True,
        "android_neural_deployed":False
    }
    meta={
        "schema":MODEL_SCHEMA,
        "parent_source_weights_sha256":digest(path),
        "parent_form_class_names":list(FORMS),
        "old_operation_network_frozen":True,
        "parent_input_mean":old_mean.tolist(),
        "parent_input_std":old_std.tolist(),
        "identity_input_dim":ID_INPUT,
        "identity_input_mean":identity_mean.tolist(),
        "identity_input_std":identity_std.tolist(),
        "identity_cameras":["side","front","top"],
        "identity_source":"baseline-only 32x32 original Kotlin rendered views",
        "chosen_on_new_development_only":selected_method,
        "fresh_blind_source_sha256":heldout_sha,
        "android_approved":False
    }
    output.joinpath("evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    output.joinpath("lineage.json").write_text(json.dumps(meta,separators=(",",":"))+"\n")
    output.joinpath("proposals.json").write_text(json.dumps(proposal,indent=2)+"\n")
    lines=["schema="+PROPOSAL_SCHEMA,"external_mesh_used=false",
           "study_id=shape_identity_v7","count=384"]
    for variant in VARIANTS:
        for i,row in enumerate(proposal[variant]):
            for key,value in row.items():
                lines.append(f"{variant}.{i}.{key}={value}")
    output.joinpath("native_proposals.properties").write_text("\n".join(lines)+"\n")
    print("IDENTITY_LEARNING_COMPLETE "+json.dumps({
        "actual_cpu_gradient_seconds":round(accumulated,1),
        "old_operation_and_strength_preserved":True,
        "development_selected_method":selected_method,
        "new_blind_16_source_families":blind_metrics,
        "forward_GLBS_pending":384*len(VARIANTS),
        "approved_for_android":False
    }),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("new_manifest","new_images","new_views",
                 "legacy_manifest","legacy_images","legacy_views",
                 "old_knowledge","out"):
        p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    p.add_argument("--training-seconds",type=int,default=1800)
    a=p.parse_args()
    train(a.new_manifest,a.new_images,a.new_views,
          a.legacy_manifest,a.legacy_images,a.legacy_views,
          a.old_knowledge,a.out,a.training_seconds)


if __name__=="__main__":
    main()

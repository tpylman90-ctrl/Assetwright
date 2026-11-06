"""Forge Mini v8: physically accurate native geometry while preserving forms.

Research-only: a FROZEN original v6 action/strength model and a FROZEN
experimentally successful (but NOT promoted) v7 hard-form identity encoder.
A small ORIGINAL residual action/strength adapter learns from source-hashed
native GLBs. No pretrained external models, external mesh generator or
automatic Android deployment.

Three equal-budget arms:
 - supervised_replay: learn operations/strengths with replay and distillation
 - physical_replay: same plus differentiable ORIGINAL Kotlin vertex loss
 - hard_physical: same plus correct-label mistake-focused native sampling
No source labels are ever used as neural model inputs. Development selects
checkpoints and methods; 16 fresh blind forms remain unseen until frozen.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import time

from advanced_form_student import OPERATIONS
from dino_delta_school import STUDY,FAMILIES,LEVELS,checked_manifest,hash_file
from dino_delta_student import INPUT_DIM,image_features
from native_multiform_student import FORMS
from native_shape_identity_views import SCHEMA as VIEWS,features,INPUT_DIM as SHAPE_INPUT
from native_multiform_vertex import prepare
from native_vertex_supervision import proxy_loss,difficulty_scores

SCHEMA="assetwright-original-form-conditioned-geometry-fidelity-v8"
WEIGHT_SCHEMA="assetwright-original-residual-native-geometry-student-v8"
PROPOSAL_SCHEMA="assetwright-original-v8-geometry-fidelity-predictions"
STUDY_NAME="form_fidelity_v8"
CONDITIONS=("supervised_replay","physical_replay","hard_physical")
VARIANTS=("parent_v7_hard",)+CONDITIONS
SEEDS=(317,1801)


def digest(path:Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_from(manifest_path:Path,images:Path,views:Path,source:Path,
              *,study:str,allowed:tuple,validate_all:bool):
    doc=json.loads(manifest_path.read_text())
    if not (
        doc.get("schema")=="assetwright-native-before-after-observations-v1"
        and doc.get("study_id")==study
        and doc.get("generator")=="AssetWright-Kotlin-AdvancedFormLab"
        and doc.get("external_geometry_used") is False):
        raise ValueError("Untrusted original native training curriculum")
    if validate_all:
        audited=checked_manifest(doc,images)
    else:
        audited=[r for r in doc["records"] if r["split"] in allowed]
        if doc.get("paired_examples")!=1968 or doc.get("source_count")!=2040:
            raise ValueError("Older v7 source has missing original geometry")
    index=json.loads((views/"index.json").read_text())
    if index.get("schema")!=VIEWS or index.get("study_id")!=study:
        raise ValueError("Original three-view form descriptors missing")
    shapes={}
    items=[]
    seen=set()
    for row in audited:
        if row["split"] not in allowed:continue
        key=(row["split"],row["family"])
        form=row.get("archetype")
        if form not in FORMS[1:] or row["operation"] not in OPERATIONS:
            raise ValueError("Foreign operation or unrecognized original native form")
        if row["case"] in seen or not re.fullmatch(
            r"(train|development|validation)__(sf|si)_(train|dev|blind)\d\d__[a-z_]+__s\d{3}",
            row["case"]):
            raise ValueError("Repeated/malformed original native example")
        seen.add(row["case"])
        if not validate_all:
            # Keep old inspected dev / blind OUT of replay, with complete
            # evidence for the training-only source we actually use.
            if (hash_file(source/(row["case"]+".glb"))!=row["modified_glb_sha256"]
                or hash_file(source/(row["baseline_case"]+".glb"))!=row["baseline_glb_sha256"]):
                raise ValueError("Original replay native GLB was replaced")
            for role,prefix in (("before",row["baseline_case"]),("after",row["case"])):
                files=row[role+"_view_files"]
                sha=row[role+"_view_sha256"]
                for view in ("side","front_three_quarter"):
                    filename=prefix+"__"+view+".png"
                    if files[view]!=filename or hash_file(images/filename)!=sha[view]:
                        raise ValueError("Replayed source image SHA changed")
        if key not in shapes:
            shapes[key]=features(row,images,views,index)
        identity=shapes[key]
        items.append({
            "case":row["case"],"split":row["split"],
            "family":row["family"],"form":form,
            "op":row["operation"],"strength":row["strength"],
            "dims":{k:row[k] for k in ("length","width","height")},
            "segments":row["segments"],"stations":row["stations"],
            "baseline_hash":row["baseline_glb_sha256"],
            "source_hash":row["modified_glb_sha256"],
            "pixels":image_features(row,images),
            "identity":identity
        })
    return items,shapes


def train(new_manifest,new_images,new_views,new_source,
          old_manifest,old_images,old_views,old_source,
          v6_knowledge,v7_knowledge,output,seconds):
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from safetensors.torch import load_file,save_file
    if STUDY!=STUDY_NAME or not 1200<=seconds<=2400:
        raise ValueError("Fresh v8 native geometry curriculum and real CPU budget required")
    old,old_sources=rows_from(old_manifest,old_images,old_views,old_source,
        study="shape_identity_v7",allowed=("train",),validate_all=False)
    current,shapes=rows_from(new_manifest,new_images,new_views,new_source,
        study=STUDY_NAME,allowed=("train","development","validation"),
        validate_all=True)
    current_by_split={p:[r for r in current if r["split"]==p]
                      for p in ("train","development","validation")}
    if (len(old)!=1200 or
        {p:len(v) for p,v in current_by_split.items()}!={
            "train":1152,"development":288,"validation":288} or
        len(old_sources)!=40 or len(shapes)!=80):
        raise ValueError("Original v7 replay and new v8 source families incomplete")
    new=current_by_split["train"]
    dev=current_by_split["development"]
    blind=current_by_split["validation"]
    old_hash={r["source_hash"] for r in old}
    if len(old_hash)!=len(old) or old_hash & {r["source_hash"] for r in current}:
        raise ValueError("Old source GLBs overlap with new geometry/blind school")
    for rows,expected in ((old,150),(new,144),(dev,36),(blind,36)):
        total={form:sum(r["form"]==form for r in rows)
               for form in FORMS[1:]}
        if set(total.values())!={expected}:
            raise ValueError("Training or blind dataset missing a shape archetype")
    # 1,200 older and 1,152 new ORIGINAL Kotlin train transformations.
    # 64 common normalized 3D vertices, across genuinely different topology.
    source_old=prepare(old,old_source)
    source_new=prepare(new,new_source)
    source_dev=prepare(dev,new_source)
    torch.set_num_threads(min(2,torch.get_num_threads()))
    history6=json.loads((v6_knowledge/"learning_history.json").read_text())
    norm6=json.loads((v6_knowledge/"lineage.json").read_text())
    history7=json.loads((v7_knowledge/"learning_history.json").read_text())
    norm7=json.loads((v7_knowledge/"lineage.json").read_text())
    weight6=v6_knowledge/"balanced_forms.safetensors"
    weight7=v7_knowledge/"hard_form_distinctions.safetensors"
    if not (
        history6.get("research_gate")=="research_not_promoted_legacy_checkpoint_retained"
        and history7.get("research_disposition")=="research_candidate_not_promoted"
        and history6["candidate_weight_sha256"]["balanced_forms"]==digest(weight6)
        and history7["new_neural_identity_weights_SHA256"]["hard_form_distinctions"]==digest(weight7)
        and norm7["parent_source_weights_sha256"]==digest(weight6)
        and len(norm6["pixel_mean"])==INPUT_DIM
        and len(norm6["pixel_std"])==INPUT_DIM
        and len(norm7["identity_input_mean"])==SHAPE_INPUT
        and len(norm7["identity_input_std"])==SHAPE_INPUT):
        raise ValueError("Experimentally retained original parent neural weights are untrusted")
    xp=np.asarray(norm6["pixel_mean"],dtype=np.float32)
    xs=np.asarray(norm6["pixel_std"],dtype=np.float32)
    ip=np.asarray(norm7["identity_input_mean"],dtype=np.float32)
    it=np.asarray(norm7["identity_input_std"],dtype=np.float32)

    class Parent(nn.Module):
        def __init__(self):
            super().__init__()
            self.core=nn.Sequential(nn.Linear(INPUT_DIM,96),nn.Tanh(),
                                    nn.Linear(96,96),nn.Tanh())
            self.op=nn.Linear(96,len(OPERATIONS))
            self.strength=nn.Linear(96,len(OPERATIONS))
            self.physical=nn.Linear(96,6)
            self.dino=nn.Linear(96,24)
            self.form=nn.Linear(96,len(FORMS))
        def forward(self,x):
            h=self.core(x)
            return self.op(h),torch.sigmoid(self.strength(h)),h,self.form(h)

    class Identity(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder=nn.Sequential(nn.Linear(SHAPE_INPUT,128),nn.GELU(),
                                       nn.Linear(128,96),nn.GELU())
            self.classifier=nn.Linear(96,len(FORMS))
        def forward(self,x):
            h=self.encoder(x)
            return self.classifier(h),h

    class Refinement(nn.Module):
        """Native original trainable 2-head adapter, NOT a new 3D generator."""
        def __init__(self):
            super().__init__()
            self.hidden=nn.Sequential(nn.Linear(204,96),nn.Tanh(),
                                      nn.Linear(96,64),nn.Tanh())
            self.op=nn.Linear(64,6)
            self.strength=nn.Linear(64,6)
            nn.init.zeros_(self.op.weight)
            nn.init.zeros_(self.op.bias)
            nn.init.zeros_(self.strength.weight)
            nn.init.zeros_(self.strength.bias)
        def forward(self,old_logits,old_powers,old_h,identity_h):
            inp=torch.cat((old_h,identity_h,old_logits,old_powers),dim=1)
            features=self.hidden(inp)
            scores=old_logits+self.op(features)*.85
            updated=torch.sigmoid(torch.logit(
                old_powers.clamp(.001,.999))+self.strength(features))
            return scores,updated

    parent=Parent()
    parent.load_state_dict(load_file(str(weight6),device="cpu"),strict=True)
    identity=Identity()
    identity.load_state_dict(load_file(str(weight7),device="cpu"),strict=True)
    parent.eval();identity.eval()
    for layer in (parent,identity):
        for p in layer.parameters():p.requires_grad_(False)
    def tensor_rows(rows,geo=None):
        pix=np.asarray([r["pixels"] for r in rows],dtype=np.float32)
        ident=np.asarray([r["identity"] for r in rows],dtype=np.float32)
        result=[
            torch.tensor((pix-xp)/xs,dtype=torch.float32),
            torch.tensor((ident-ip)/it,dtype=torch.float32),
            torch.tensor([OPERATIONS.index(r["op"]) for r in rows],dtype=torch.long),
            torch.tensor([r["strength"] for r in rows],dtype=torch.float32),
            torch.tensor([FORMS.index(r["form"]) for r in rows],dtype=torch.long)
        ]
        if geo is not None:
            result += [
                torch.tensor(geo["basis"],dtype=torch.float32),
                torch.tensor(geo["targets"],dtype=torch.float32)
            ]
        return result
    old_t=tensor_rows(old,source_old)
    fresh_t=tensor_rows(new,source_new)
    dev_t=tensor_rows(dev,source_dev)
    # Cache all frozen features. The gradients can only update the original
    # adapter, not previously learned form or operation recognition weights.
    def cache(t):
        with torch.inference_mode():
            old_score,old_power,h,old_form=parent(t[0])
            identity_score,ih=identity(t[1])
            frozen_forms=(identity_score+.18*old_form).argmax(1)
        return (old_score.detach(),old_power.detach(),h.detach(),ih.detach(),
                frozen_forms.detach())
    old_cache=cache(old_t)
    new_cache=cache(fresh_t)
    dev_cache=cache(dev_t)
    def metrics(model,data,pred):
        model.eval()
        with torch.inference_mode():
            if model is None:
                logits,powers=pred[0],pred[1]
            else:
                logits,powers=model(*pred[:4])
            op=data[2];strength=data[3]
            predicted=logits.argmax(1)
            estimated=powers.gather(1,predicted[:,None]).flatten()
            errors=(estimated-strength).abs()
            indices=torch.arange(len(op))
            displacement=data[5][indices,predicted,:]*estimated[:,None]
            proxy=float(torch.sqrt(((displacement-data[6])**2).mean()))
            ce=float(F.cross_entropy(logits,op))
            mae=float(errors.mean())
            return {
                "operation_accuracy":float(predicted.eq(op).float().mean()),
                "strength_mae":mae,
                "strength_median_abs_error":float(errors.median()),
                "form_accuracy":float(pred[4].eq(data[4]).float().mean()),
                "native_3D_displacement_proxy_rmse":proxy,
                "classification_loss":ce,
                # Development-only checkpoint selector, NO blind used.
                "development_priority":.40*ce+1.8*mae+45.*proxy
            }
    prior_old=metrics(None,old_t,old_cache)
    prior_dev=metrics(None,dev_t,dev_cache)
    output.mkdir(parents=True,exist_ok=True)
    (output/"sessions").mkdir(exist_ok=True)
    (output/"winners").mkdir(exist_ok=True)
    training_time=seconds/(len(CONDITIONS)*len(SEEDS))
    sessions=[]
    champions={}
    dev_results={}
    spent=0.
    for condition in CONDITIONS:
        best_cond=float("inf");selected_state=None;selected_meta=None
        for seed in SEEDS:
            torch.manual_seed(seed)
            model=Refinement()
            optimizer=torch.optim.AdamW(model.parameters(),lr=.00043,
                                        weight_decay=.0007)
            best=float("inf");chosen=None;chosen_step=0
            step=0;last_log=time.perf_counter();start=last_log
            # One uniform floor: hard examples never suppress the easy forms.
            difficulty=torch.full((len(new),),1./len(new))
            while time.perf_counter()-start<training_time or step<100:
                old_idx=torch.randint(len(old),(64,))
                if condition=="hard_physical":
                    new_idx=torch.multinomial(difficulty,96,replacement=True)
                else:
                    new_idx=torch.randint(len(new),(96,))
                cache_batch=[
                    torch.cat((a[new_idx],b[old_idx]),0)
                    for a,b in zip(new_cache,old_cache)
                ]
                op=torch.cat((fresh_t[2][new_idx],old_t[2][old_idx]))
                power=torch.cat((fresh_t[3][new_idx],old_t[3][old_idx]))
                basis=torch.cat((fresh_t[5][new_idx],old_t[5][old_idx]))
                targets=torch.cat((fresh_t[6][new_idx],old_t[6][old_idx]))
                scores,heads=model(*cache_batch[:4])
                guessed=heads.gather(1,op[:,None]).flatten()
                loss=.90*F.cross_entropy(scores,op)
                loss+=5.0*F.smooth_l1_loss(guessed,power,beta=.08)
                if condition!="supervised_replay":
                    loss+=proxy_loss(scores,heads,basis,targets,op)
                # Explicitly retain old learned responses on replay.
                loss+=.16*F.mse_loss(scores[96:],cache_batch[0][96:])
                loss+=.20*F.mse_loss(heads[96:],cache_batch[1][96:])
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(),2.)
                optimizer.step()
                step+=1
                if condition=="hard_physical" and step%240==0:
                    with torch.inference_mode():
                        p,h=model(*new_cache[:4])
                        mistakes=difficulty_scores(p,h,fresh_t[2],fresh_t[3])
                        norm=(mistakes-mistakes.mean())/(mistakes.std()+1e-6)
                        # Native twist and known difficult form families get
                        # extra sampling only from TRUE source labels.
                        boost=torch.tensor([
                            1.55 if r["op"]=="SECTION_TWIST" or
                                     r["form"] in ("SPINDLE","TRUSS_BEAM")
                            else 1.0 for r in new],dtype=torch.float32)
                        scores=torch.softmax(norm.clamp(-3,3),dim=0)*boost
                        scores=scores/scores.sum()
                        difficulty=.40/len(new)+.60*scores
                if step%100==0:
                    stats=metrics(model,dev_t,dev_cache)
                    retained=metrics(model,old_t,old_cache)
                    old_ok=(
                        retained["operation_accuracy"]>=
                            prior_old["operation_accuracy"]-.025
                        and retained["strength_mae"]<=
                            prior_old["strength_mae"]+.020)
                    if old_ok and stats["development_priority"]<best:
                        best=stats["development_priority"]
                        chosen={k:v.detach().cpu().clone()
                                for k,v in model.state_dict().items()}
                        chosen_step=step
                    now=time.perf_counter()
                    if now-last_log>29:
                        print("FIDELITY_OPT "+json.dumps({
                            "mode":condition,"seed":seed,"updates":step,
                            "optimizer_seconds":round(now-start,2),
                            "dev_real_vertex_proxy":stats["native_3D_displacement_proxy_rmse"],
                            "old_knowledge_retained":old_ok,
                            "chosen_step":chosen_step}),flush=True)
                        last_log=now
            elapsed=time.perf_counter()-start
            spent+=elapsed
            if chosen is None:
                # Persist a genuine full-trained candidate even if it fails
                # historical retention: don't silently claim promotion.
                chosen={k:v.detach().cpu().clone()
                        for k,v in model.state_dict().items()}
                chosen_step=step
            model.load_state_dict(chosen,strict=True)
            performance=metrics(model,dev_t,dev_cache)
            retention=metrics(model,old_t,old_cache)
            save_file({k:v.detach().cpu().contiguous()
                       for k,v in model.state_dict().items()},
                      output/"sessions"/f"{condition}__{seed}.safetensors")
            sessions.append({
                "condition":condition,"seed":seed,
                "actual_optimizer_seconds":round(elapsed,3),
                "optimizer_updates":step,
                "selected_development_step":chosen_step,
                "new_development":performance,
                "old_training_retention":retention
            })
            if performance["development_priority"]<best_cond:
                best_cond=performance["development_priority"]
                selected_state=copy.deepcopy(chosen)
                selected_meta={"seed":seed,"selected_step":chosen_step}
            print("FIDELITY_SESSION_DONE "+json.dumps({
                "condition":condition,"seed":seed,
                "training_seconds":round(elapsed,3),
                "development_priority":performance["development_priority"]
            }),flush=True)
        winner=Refinement()
        winner.load_state_dict(selected_state,strict=True)
        champions[condition]=winner
        dev_results[condition]=metrics(winner,dev_t,dev_cache)
        save_file({k:v.detach().cpu().contiguous()
                   for k,v in winner.state_dict().items()},
                  output/"winners"/(condition+".safetensors"))
    if spent<seconds:raise ValueError("CPU-gradient training duration not actually met")
    method=min(CONDITIONS,key=lambda name:dev_results[name]["development_priority"])

    # No blind images or oracle native geometry was opened for any
    # optimizer, checkpoint/seed selection or method selection.
    blind_t=tensor_rows(blind)
    blind_cache=cache(blind_t)
    proposal={
        "schema":PROPOSAL_SCHEMA,"study_id":STUDY_NAME,
        "external_mesh_used":False,"count":len(blind)
    }
    blind_results={}
    def infer(model):
        with torch.inference_mode():
            if model is None:
                logits,powers=blind_cache[0],blind_cache[1]
            else:
                logits,powers=model(*blind_cache[:4])
            op=logits.argmax(1)
            power=powers.gather(1,op[:,None]).flatten()
            guessed_forms=blind_cache[4]
        return op.tolist(),power.tolist(),guessed_forms.tolist()
    for name,model in [("parent_v7_hard",None)]+list(champions.items()):
        indices,powers,form_indices=infer(model)
        proposals=[]
        for i,row in enumerate(blind):
            proposals.append({
                "case":row["case"],
                "source_glb_sha256":row["source_hash"],
                "baseline_glb_sha256":row["baseline_hash"],
                "predicted_operation":OPERATIONS[indices[i]],
                "predicted_strength":round(float(powers[i]),7),
                "predicted_archetype":FORMS[form_indices[i]],
                **row["dims"]
            })
        proposal[name]=proposals
        blind_results[name]={
            "form_accuracy":sum(
                form_indices[i]==FORMS.index(r["form"])
                for i,r in enumerate(blind))/len(blind),
            "operation_accuracy":sum(
                indices[i]==OPERATIONS.index(r["op"])
                for i,r in enumerate(blind))/len(blind),
            "strength_mae":sum(
                abs(powers[i]-r["strength"])
                for i,r in enumerate(blind))/len(blind),
            "predicted_distinct_forms":len(set(form_indices)-{0})
        }
    sha=hashlib.sha256("\n".join(sorted(
        r["source_hash"] for r in blind)).encode()).hexdigest()
    report={
        "schema":SCHEMA,"study":STUDY_NAME,
        "old_v6_experimental_parent_sha256":digest(weight6),
        "old_v7_experimental_identity_sha256":digest(weight7),
        "both_existing_neural_networks_frozen":True,
        "older_correct_original_train_sources":len(old),
        "new_original_shape_train_examples":len(new),
        "new_development_examples":len(dev),
        "new_fresh_unseen_blind_examples":len(blind),
        "new_shape_train_families":len({r["family"] for r in new}),
        "fresh_blind_form_families":len({r["family"] for r in blind}),
        "three_methods_equal_start_and_cpu_time":True,
        "measured_optimizer_seconds":round(spent,3),
        "configured_optimizer_seconds":seconds,
        "completed_sessions":len(sessions),
        "sessions":sessions,
        "previous_training_retention_before":prior_old,
        "previous_development_before":prior_dev,
        "development_results":dev_results,
        "development_selected":method,
        "blind_source_sha256":sha,
        "blind_per_method_predictions":blind_results,
        "geometry_supervision_only_original_kotlin_GLBS":True,
        "external_teacher_used":False,
        "android_neural_deployed":False
    }
    lineage={
        "schema":WEIGHT_SCHEMA,
        "source_v6_weight_sha256":digest(weight6),
        "source_v7_form_weight_sha256":digest(weight7),
        "input_original_action_dim":INPUT_DIM,
        "input_original_form_dim":SHAPE_INPUT,
        "form_classes":list(FORMS),"ops":list(OPERATIONS),
        "legacy_action_weights_frozen":True,
        "legacy_shape_identity_weights_frozen":True,
        "final_method_selected_by_new_development":method,
        "blind_source_sha256":sha,
        "not_approved_for_android":True
    }
    (output/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (output/"lineage.json").write_text(json.dumps(lineage,indent=2)+"\n")
    (output/"proposals.json").write_text(json.dumps(proposal,indent=2)+"\n")
    props=["schema="+PROPOSAL_SCHEMA,"study_id="+STUDY_NAME,
           "external_mesh_used=false","count="+str(len(blind))]
    for name in VARIANTS:
        for i,row in enumerate(proposal[name]):
            for key,value in row.items():
                props.append(f"{name}.{i}.{key}={value}")
    (output/"native_proposals.properties").write_text("\n".join(props)+"\n")
    print("FORM_FIDELITY_TRAINING_COMPLETE "+json.dumps({
        "trained_gradient_seconds":round(spent,3),
        "original_previous_models_frozen":True,
        "development_selected":method,
        "new_blind_metrics":blind_results,
        "actual_kotlin_geometry_audit_pending":True
    }),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in (
        "new_manifest","new_images","new_views","new_source",
        "old_manifest","old_images","old_views","old_source",
        "v6_knowledge","v7_knowledge","out"):
        p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    p.add_argument("--training-seconds",type=int,default=1800)
    a=p.parse_args()
    train(a.new_manifest,a.new_images,a.new_views,a.new_source,
          a.old_manifest,a.old_images,a.old_views,a.old_source,
          a.v6_knowledge,a.v7_knowledge,a.out,a.training_seconds)


if __name__=="__main__":
    main()

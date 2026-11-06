"""Forge Mini v6: genuinely different SHAPES, not one universal mesh.

Starts from the verified original neural checkpoint. Learns to CLASSIFY
eight distinct native geometry archetypes as well as six operations and
continuous strengths, using correctly labelled original Kotlin GLBs.

The old student has no form head, so its established weights load exactly
and a NEW form head is trained without replacing its old representations.
1,680 historical training-only examples are replayed. 672 new original
multi-form training cases teach distinct cross sections and topology.
Each experiment gets equal active CPU training seconds.

No exposed past validation case, DINO model, or external mesh generator
is used. 192 new source-family validation cases are frozen until AFTER
development-only checkpoint and method selection. No Android promotion.
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
from dino_delta_student import INPUT_DIM,image_features
from dino_delta_school import STUDY,FAMILIES,LEVELS,checked_manifest,hash_file
from native_studied_warm_start import load_provenance,warm_start
from native_geometry_aware_student import old_replay
from native_multiform_vertex import prepare,proxy_loss

FORMS=("LEGACY_SHELL","SPINDLE","WEDGE","BOX_MODULE","BARREL",
       "ARCH","BLADE","CANOPY_POD","TRUSS_BEAM")
CONDITIONS=("balanced_forms","geometry_forms","geometry_hard_forms")
VARIANTS=("prior",)+CONDITIONS
SEEDS=(157,1801)
SCHEMA="assetwright-8-archetype-neural-continuation-v6"
MODEL_SCHEMA="assetwright-original-8-archetype-neural-weights-v6"
PROPOSAL_SCHEMA="assetwright-native-multiform-128-program-proposals-v6"


def replay_v5(manifest,images:Path,source:Path):
    if (manifest.get("schema")!="assetwright-native-before-after-observations-v1"
        or manifest.get("study_id")!="geometry_aware_v5"
        or manifest.get("paired_examples")!=696
        or manifest.get("source_count")!=716
        or manifest.get("generator")!="AssetWright-Kotlin-AdvancedFormLab"
        or manifest.get("external_geometry_used") is not False):
        raise ValueError("V5 source hash replay provenance invalid")
    rows=[]
    for row in manifest.get("records",[]):
        if row.get("split")!="train":
            continue
        family=row.get("family")
        op=row.get("operation")
        strength=row.get("strength")
        if (not isinstance(family,str)
            or not re.fullmatch(r"bg_train(0[1-9]|1[0-2])",family)
            or op not in OPERATIONS
            or type(strength) not in (float,int)
            or not any(abs(strength-v)<1e-5
                       for v in (.02,.14,.30,.46,.63,.81,.99))):
            raise ValueError("Historical v5 training form/strength invalid")
        stem=f"train__{family}__{op.lower()}__s{round(strength*1000):03d}"
        base=f"train__{family}__baseline"
        if row.get("case")!=stem or row.get("baseline_case")!=base:
            raise ValueError("Historical candidate source identity differs")
        for name,key in ((stem,"modified_glb_sha256"),(base,"baseline_glb_sha256")):
            file=source/(name+".glb")
            if hash_file(file)!=row.get(key):
                raise ValueError("Original v5 source shape hash missing")
        for kind,name in (("before",base),("after",stem)):
            views=row.get(kind+"_view_files",{})
            hashes=row.get(kind+"_view_sha256",{})
            if set(views)!={"side","front_three_quarter"} or set(hashes)!=set(views):
                raise ValueError("Prior image alignment incomplete")
            for view,actual in views.items():
                file=images/(name+"__"+view+".png")
                if file.name!=actual or hash_file(file)!=hashes[view]:
                    raise ValueError("Source v5 original image SHA differs")
        rows.append({
            "case":stem,"family":family,"split":"train",
            "op":op,"strength":strength,
            "source_hash":row["modified_glb_sha256"],
            "x":image_features(row,images),
            "morph":row["measured_morphology_delta"],
            "form":"LEGACY_SHELL"
        })
    if len(rows)!=504 or len({r["source_hash"] for r in rows})!=504:
        raise ValueError("Exactly 504 original v5 TRAINING examples needed")
    return rows


def new_rows(manifest,images:Path):
    if STUDY!="multiform_v6":
        raise ValueError("Must enable original multiform study")
    rows=checked_manifest(manifest,images)
    partitions={name:[] for name in ("train","development","validation")}
    for row in rows:
        phase=row["split"]
        if row.get("archetype") not in FORMS[1:]:
            raise ValueError("No valid original multiple-form source label")
        partitions[phase].append({
            "case":row["case"],"split":phase,"family":row["family"],
            "op":row["operation"],"strength":row["strength"],
            "x":image_features(row,images),
            "morph":row["measured_morphology_delta"],
            "form":row["archetype"],
            "segments":row["segments"],"stations":row["stations"],
            "source_hash":row["modified_glb_sha256"],
            "baseline_hash":row["baseline_glb_sha256"],
            "dims":{k:row[k] for k in ("length","width","height")}
        })
    if {k:len(v) for k,v in partitions.items()}!={
        "train":672,"development":192,"validation":192}:
        raise ValueError("One or more NEW 8-form source families missing")
    for phase,items in partitions.items():
        form_count={name:sum(x["form"]==name for x in items) for name in FORMS[1:]}
        desired=84 if phase=="train" else 24
        if set(form_count.values())!={desired}:
            raise ValueError("A model could collapse shapes without balanced real archetypes")
        families=FAMILIES[phase]
        if len(families)!=len({x["family"] for x in items}):
            raise ValueError("Missing separate original form families")
    keys=[item["source_hash"] for group in partitions.values() for item in group]
    if len(set(keys))!=len(keys):
        raise ValueError("New original multi-form native GLB duplication")
    return partitions


def train(v6_manifest,v6_images,v6_source,
          v3_manifest,v3_images,v3_source,
          v4_manifest,v4_images,v4_source,
          v5_manifest,v5_images,v5_source,
          knowledge,output,training_seconds):
    import numpy as np
    import torch
    import torch.nn.functional as F
    from torch import nn
    from safetensors.torch import save_file,load_file
    if not 1200<=training_seconds<=2400:
        raise ValueError("Training budget must be 20–40 active optimizer minutes")
    lineage,normalization,_=load_provenance(knowledge)
    old3=old_replay(v3_manifest,v3_images,v3_source,"strength_marathon_v3")
    old4=old_replay(v4_manifest,v4_images,v4_source,"strength_continual_v4")
    old5=replay_v5(v5_manifest,v5_images,v5_source)
    # Retain correct original labels, NOT any rejected candidate model weights.
    old=[]
    for case in old3+old4+old5:
        old.append({**case,"form":"LEGACY_SHELL"})
    new=new_rows(v6_manifest,v6_images)
    if len(old)!=1680 or len(new["train"])!=672:
        raise ValueError("Incomplete 1680 original replay / 672 multi-form curriculum")
    old_sha={x["source_hash"] for x in old}
    new_sha={x["source_hash"] for phase in new.values() for x in phase}
    if old_sha&new_sha:
        raise ValueError("Previously seen source mesh leaked into new blind test")
    physical=prepare(new["train"],v6_source)
    dev_physical=prepare(new["development"],v6_source)
    all_rows=old+new["train"]
    pixels=np.asarray([r["x"] for r in all_rows],dtype=np.float32)
    mean=pixels.mean(axis=0)
    standard=np.maximum(pixels.std(axis=0),.06)
    morph=np.asarray([r["morph"] for r in all_rows],dtype=np.float32)
    morph_scale=np.maximum(morph.std(axis=0),.07)
    torch.set_num_threads(min(2,torch.get_num_threads()))
    def as_tensor(rows,geometry=None):
        x=(np.asarray([r["x"] for r in rows],dtype=np.float32)-mean)/standard
        result=[
            torch.tensor(x,dtype=torch.float32),
            torch.tensor([OPERATIONS.index(r["op"]) for r in rows],dtype=torch.long),
            torch.tensor([r["strength"] for r in rows],dtype=torch.float32),
            torch.tensor([FORMS.index(r["form"]) for r in rows],dtype=torch.long),
            torch.tensor(np.asarray([r["morph"] for r in rows],dtype=np.float32)
                /morph_scale,dtype=torch.float32)
        ]
        if geometry is not None:
            result.extend((torch.tensor(geometry["basis"],dtype=torch.float32),
                           torch.tensor(geometry["targets"],dtype=torch.float32)))
        return result
    oldt=as_tensor(old)
    newt=as_tensor(new["train"],physical)
    devt=as_tensor(new["development"],dev_physical)

    class Student(nn.Module):
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
            features=self.core(x)
            return (self.op(features),torch.sigmoid(self.strength(features)),
                    self.physical(features),self.form(features))

    class OldStudent(nn.Module):
        def __init__(self):
            super().__init__()
            self.core=nn.Sequential(nn.Linear(INPUT_DIM,96),nn.Tanh(),
                                    nn.Linear(96,96),nn.Tanh())
            self.op=nn.Linear(96,len(OPERATIONS))
            self.strength=nn.Linear(96,len(OPERATIONS))
            self.physical=nn.Linear(96,6)
            self.dino=nn.Linear(96,24)
        def forward(self,x):
            h=self.core(x)
            return (self.op(h),torch.sigmoid(self.strength(h)),
                    self.physical(h),self.dino(h))

    original=OldStudent()
    warm=warm_start(original,mean,standard,knowledge)
    prior_raw=OldStudent()
    prior_raw.load_state_dict(load_file(str(
        knowledge/"owned_native_student.safetensors"),device="cpu"),strict=True)
    old_pixels=(np.asarray([r["x"] for r in old],dtype=np.float32)
        -np.asarray(normalization["train_feature_mean"],dtype=np.float32)) \
        /np.asarray(normalization["train_feature_std"],dtype=np.float32)
    with torch.no_grad():
        unchanged=float((original(oldt[0])[0]-prior_raw(
            torch.tensor(old_pixels,dtype=torch.float32))[0]).abs().max())
    if unchanged>.002:
        raise ValueError("Prior original neural learning was not actually preserved")

    torch.manual_seed(4572026)
    initialized=Student()
    original_state=original.state_dict()
    state=initialized.state_dict()
    for key,value in original_state.items():
        state[key]=value.detach().cpu().clone()
    initialized.load_state_dict(state,strict=True)
    frozen_start=copy.deepcopy(initialized.state_dict())
    with torch.no_grad():
        old_logits,old_strength,_,_=initialized(oldt[0])

    def stats(model,batch,*,include_proxy=True):
        model.eval()
        with torch.no_grad():
            op_scores,powers,_,form_scores=model(batch[0])
            actual_op,truth,actual_form=batch[1],batch[2],batch[3]
            guess_op=op_scores.argmax(1)
            guess_form=form_scores.argmax(1)
            guessed_strength=powers.gather(1,guess_op[:,None]).flatten()
            ce=float(F.cross_entropy(op_scores,actual_op))
            form_ce=float(F.cross_entropy(form_scores,actual_form))
            mae=float((guessed_strength-truth).abs().mean())
            result={
                "operation_accuracy":float((guess_op==actual_op).float().mean()),
                "strength_mae":mae,
                "form_accuracy":float((guess_form==actual_form).float().mean()),
                "distinct_predicted_forms":len(set(guess_form.tolist())),
                "form_cross_entropy":form_ce,"operation_cross_entropy":ce
            }
            if include_proxy and len(batch)>5:
                # A DEV-only physical proxy supplements real 3D verification.
                idx=torch.arange(len(guess_op))
                predicted=batch[5][idx,guess_op,:]*guessed_strength[:,None]
                proxy=float(torch.sqrt(((predicted-batch[6])**2).mean()))
                result["physical_proxy_rmse"]=proxy
                result["development_priority"]=(
                    1.3*form_ce+.45*ce+2.0*mae+28.*proxy)
            return result

    previous_old={
        "operation_accuracy":float((original(oldt[0])[0].argmax(1)
                                   ==oldt[1]).float().mean()),
    }
    with torch.no_grad():
        prior_op,prior_strength,_,_=original(oldt[0])
        pred=prior_op.argmax(1)
        previous_old["strength_mae"]=float((
            prior_strength.gather(1,pred[:,None]).flatten()-oldt[2]).abs().mean())

    output.mkdir(parents=True,exist_ok=True)
    (output/"sessions").mkdir(exist_ok=True)
    (output/"winners").mkdir(exist_ok=True)
    budget=training_seconds/(len(CONDITIONS)*len(SEEDS))
    completed=[]
    model_winners={}
    selected={}
    seconds=0.
    for condition in CONDITIONS:
        champ=None
        champ_info=None
        best=float("inf")
        for seed in SEEDS:
            torch.manual_seed(seed)
            model=Student()
            model.load_state_dict(copy.deepcopy(frozen_start),strict=True)
            optimizer=torch.optim.AdamW(model.parameters(),lr=.00043,
                                        weight_decay=.0008)
            best_state=None;best_step=0;best_score=float("inf")
            new_prob=torch.full((len(new["train"]),),1/len(new["train"]))
            start=time.perf_counter()
            step=0
            last=start
            while time.perf_counter()-start<budget or step<80:
                oi=torch.randint(len(old),(64,))
                if condition=="geometry_hard_forms":
                    ni=torch.multinomial(new_prob,96,replacement=True)
                else:
                    # Stratify by actual archetype so each minibatch learns
                    # all 8 object shape types, not the dominant generic form.
                    id_by_form=[
                        torch.tensor([i for i,r in enumerate(new["train"])
                                      if r["form"]==form],dtype=torch.long)
                        for form in FORMS[1:]
                    ]
                    ni=torch.cat([ids[torch.randint(len(ids),(12,))]
                                  for ids in id_by_form])
                x=torch.cat((oldt[0][oi],newt[0][ni]),0)
                op=torch.cat((oldt[1][oi],newt[1][ni]),0)
                strength=torch.cat((oldt[2][oi],newt[2][ni]),0)
                form=torch.cat((oldt[3][oi],newt[3][ni]),0)
                shape=torch.cat((oldt[4][oi],newt[4][ni]),0)
                op_logits,heads,morph_pred,form_logits=model(
                    x+.007*torch.randn_like(x))
                chosen=heads.gather(1,op[:,None]).flatten()
                loss=.9*F.cross_entropy(op_logits,op)
                loss+=4.7*F.smooth_l1_loss(chosen,strength,beta=.09)
                loss+=1.4*F.cross_entropy(form_logits,form)
                loss+=.10*F.smooth_l1_loss(morph_pred,shape,beta=.2)
                if condition!="balanced_forms":
                    loss+=proxy_loss(
                        op_logits[64:],heads[64:],form_logits[64:],
                        op[64:],form[64:],
                        newt[5][ni],newt[6][ni])
                old_scores,old_heads,_,_=model(oldt[0][oi])
                loss+=.17*F.mse_loss(old_scores,old_logits[oi])
                loss+=.21*F.mse_loss(old_heads,old_strength[oi])
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(),2.)
                optimizer.step()
                step+=1
                if condition=="geometry_hard_forms" and step%240==0:
                    # Reweigh ONLY real labeled TRAIN examples. 40% uniform
                    # probability maintains all archetypes in circulation.
                    with torch.no_grad():
                        logits,powers,_,forms=model(newt[0])
                        indices=torch.arange(len(new["train"]))
                        op_error=F.cross_entropy(logits,newt[1],reduction="none")
                        form_error=F.cross_entropy(forms,newt[3],reduction="none")
                        strength_error=(powers[indices,newt[1]]-newt[2]).abs()
                        errors=op_error+1.5*form_error+strength_error
                        normalized=(errors-errors.mean())/(errors.std()+1.e-6)
                        new_prob=.4/len(errors)+.6*torch.softmax(
                            normalized.clamp(-3,3),dim=0)
                if step%80==0:
                    dev=stats(model,devt)
                    old_report=stats(model,oldt,include_proxy=False)
                    retained=(
                        old_report["operation_accuracy"]>=
                            previous_old["operation_accuracy"]-.025
                        and old_report["strength_mae"]<=
                            previous_old["strength_mae"]+.02
                        and old_report["form_accuracy"]>=.90
                    )
                    # v6 candidate must learn actual multiple form classes,
                    # not win by predicting the old generic shell for all.
                    diverse=(dev["distinct_predicted_forms"]>=6 and
                             dev["form_accuracy"]>=.58)
                    if (retained and diverse and
                        dev["development_priority"]<best_score):
                        best_score=dev["development_priority"]
                        best_step=step
                        best_state={k:v.detach().cpu().clone()
                                    for k,v in model.state_dict().items()}
                    now=time.perf_counter()
                    if now-last>28:
                        print("MULTIFORM_OPT "+json.dumps({
                            "condition":condition,"seed":seed,"updates":step,
                            "measured_active_seconds":round(now-start,2),
                            "dev_shape_accuracy":dev["form_accuracy"],
                            "dev_unique_forms":dev["distinct_predicted_forms"],
                            "old_knowledge_retained":retained,
                            "best_dev_priority":best_score
                        }),flush=True)
                        last=now
            elapsed=time.perf_counter()-start
            seconds+=elapsed
            if best_state is None:
                # Never silently treat random initialization as learning.
                raise ValueError("Student never learned diversified forms while retaining old skills")
            model.load_state_dict(best_state,strict=True)
            performance=stats(model,devt)
            history={
                "condition":condition,"seed":seed,
                "actual_optimizer_seconds":round(elapsed,3),
                "optimizer_updates":step,
                "dev_selected_step":best_step,
                "development":performance,
                "replayed_prior":stats(model,oldt,include_proxy=False)
            }
            completed.append(history)
            save_file({k:v.detach().cpu().contiguous()
                       for k,v in model.state_dict().items()},
                      output/"sessions"/f"{condition}__{seed}.safetensors")
            if performance["development_priority"]<best:
                best=performance["development_priority"]
                champ=copy.deepcopy(best_state)
                champ_info={"seed":seed,"selected_step":best_step}
            print("MULTIFORM_SESSION "+json.dumps(history),flush=True)
        winner=Student()
        winner.load_state_dict(champ,strict=True)
        model_winners[condition]=winner
        selected[condition]=champ_info
        save_file({k:v.detach().cpu().contiguous()
                   for k,v in winner.state_dict().items()},
                  output/"winners"/(condition+".safetensors"))
    if seconds<training_seconds:
        raise ValueError("Not enough verified active CPU-gradient training")

    dev_report={k:stats(model,devt) for k,model in model_winners.items()}
    selected_method=min(CONDITIONS,
        key=lambda k:dev_report[k]["development_priority"])
    blind=new["validation"]
    blind_x=torch.tensor(
        (np.asarray([r["x"] for r in blind],dtype=np.float32)-mean)/standard,
        dtype=torch.float32)
    proposals={
        "schema":PROPOSAL_SCHEMA,
        "external_mesh_used":False,
        "count":len(blind),"study_id":"multiform_v6"
    }
    results={}
    # Parent original model has NO form head. It predicts a generic shell.
    models={"prior":None,**model_winners}
    for name,model in models.items():
        if model is None:
            original.eval()
            with torch.no_grad():
                op_logits,powers,_,_=original(blind_x)
                predicted_form=torch.zeros(len(blind),dtype=torch.long)
        else:
            model.eval()
            with torch.no_grad():
                op_logits,powers,_,form_logits=model(blind_x)
                predicted_form=form_logits.argmax(dim=1)
        predicted_op=op_logits.argmax(dim=1)
        predicted_strength=powers.gather(
            1,predicted_op[:,None]).flatten()
        per_form={}
        for form in FORMS[1:]:
            ix=[i for i,row in enumerate(blind) if row["form"]==form]
            per_form[form]={
                "count":len(ix),
                "form_correct":sum(int(predicted_form[i])==FORMS.index(form)
                                   for i in ix),
                "operation_correct":sum(
                    int(predicted_op[i])==OPERATIONS.index(blind[i]["op"])
                    for i in ix)
            }
        result={
            "form_accuracy":sum(
                int(predicted_form[i])==FORMS.index(row["form"])
                for i,row in enumerate(blind))/len(blind),
            "operation_accuracy":sum(
                int(predicted_op[i])==OPERATIONS.index(row["op"])
                for i,row in enumerate(blind))/len(blind),
            "strength_mae":sum(
                abs(float(predicted_strength[i])-row["strength"])
                for i,row in enumerate(blind))/len(blind),
            "distinct_predicted_archetypes":len(set(
                FORMS[int(x)] for x in predicted_form.tolist()
                if int(x)!=0)),
            "per_form":per_form
        }
        results[name]=result
        props=[]
        for i,row in enumerate(blind):
            props.append({
                "case":row["case"],
                "source_glb_sha256":row["source_hash"],
                "baseline_glb_sha256":row["baseline_hash"],
                "predicted_operation":OPERATIONS[int(predicted_op[i])],
                "predicted_strength":round(float(predicted_strength[i]),7),
                "predicted_archetype":FORMS[int(predicted_form[i])],
                **row["dims"]
            })
        proposals[name]=props
    blind_hash=hashlib.sha256("\n".join(sorted(
        row["source_hash"] for row in blind)).encode()).hexdigest()
    report={
        "schema":SCHEMA,"study_id":"multiform_v6",
        "parent_sha256":lineage["saved_weights_sha256"],
        "previous_owned_parameters_reused":lineage["parameter_count"],
        "unmodified_parent_predictions_max_abs_error":unchanged,
        "old_original_replay_cases":len(old),
        "new_multiform_train_examples":len(new["train"]),
        "new_multiform_dev_examples":len(new["development"]),
        "fresh_never_inspected_blind_examples":len(blind),
        "training_archetypes":list(FORMS[1:]),
        "train_family_count":len(FAMILIES["train"]),
        "validation_family_count":len(FAMILIES["validation"]),
        "source_topologies":("24x24","32x24","32x32","40x32"),
        "test_topology_never_trained":True,
        "original_kotlin_vertex_supervision_sha":physical["source_sha256"],
        "training_sessions":len(completed),"session_results":completed,
        "actual_optimizer_seconds":round(seconds,3),
        "required_optimizer_seconds":training_seconds,
        "same_cpu_budget_and_start":True,
        "development_winner_per_method":selected,
        "development_only_method_selected":selected_method,
        "development_scores":dev_report,
        "blind_source_sha256":blind_hash,
        "frozen_blind_results":results,
        "prior_old_training_metrics":previous_old,
        "continued_old_training_metrics":{
            name:stats(model,oldt,include_proxy=False)
            for name,model in model_winners.items()
        },
        "replay_old_model_retained":True,
        "outside_geometry_model_used":False,
        "android_deployed":False
    }
    normalization={
        "schema":MODEL_SCHEMA,
        "source_parent_sha256":lineage["saved_weights_sha256"],
        "input_features":INPUT_DIM,"hidden_dim":96,
        "form_names":list(FORMS),"operations":list(OPERATIONS),
        "pixel_mean":mean.tolist(),"pixel_std":standard.tolist(),
        "morph_std":morph_scale.tolist(),
        "development_selected_method":selected_method,
        "blind_source_sha256":blind_hash,
        "android_deployable":False,
        "human_review_required":True
    }
    output.joinpath("evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    output.joinpath("lineage.json").write_text(json.dumps(normalization,separators=(",",":"))+"\n")
    output.joinpath("proposals.json").write_text(json.dumps(proposals,indent=2)+"\n")
    lines=["schema="+PROPOSAL_SCHEMA,"external_mesh_used=false",
           "study_id=multiform_v6","count="+str(len(blind))]
    for mode in VARIANTS:
        for idx,row in enumerate(proposals[mode]):
            for key,value in row.items():
                lines.append(f"{mode}.{idx}.{key}={value}")
    output.joinpath("native_proposals.properties").write_text(
        "\n".join(lines)+"\n")
    print("MULTIFORM_BLIND_FROZEN "+json.dumps({
        "actual_optimizer_seconds":round(seconds,3),
        "loaded_original_parent":lineage["saved_weights_sha256"],
        "original_correct_training_lessons":len(old),
        "eight_original_forms_train":True,
        "blind_results":results,
        "selected_development_method":selected_method,
        "native_glb_audit_pending":True,
        "android_deployed":False
    }),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("new_manifest","new_images","new_source",
                 "v3_manifest","v3_images","v3_source",
                 "v4_manifest","v4_images","v4_source",
                 "v5_manifest","v5_images","v5_source",
                 "knowledge","out"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    p.add_argument("--training-seconds",type=int,default=1800)
    a=p.parse_args()
    train(
        json.loads(a.new_manifest.read_text()),a.new_images,a.new_source,
        json.loads(a.v3_manifest.read_text()),a.v3_images,a.v3_source,
        json.loads(a.v4_manifest.read_text()),a.v4_images,a.v4_source,
        json.loads(a.v5_manifest.read_text()),a.v5_images,a.v5_source,
        a.knowledge,a.out,a.training_seconds)


if __name__=="__main__":
    main()

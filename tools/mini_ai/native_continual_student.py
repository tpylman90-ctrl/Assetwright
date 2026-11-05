"""Genuine Forge Mini continual learning: persist, reload, REPLAY, UPDATE.

Starts from original checkpoint 42080318206 (160,938 learned parameters).
Rehearses 672 old native source examples and 504 NEW source examples,
selects checkpoints with 96 fresh development examples, and evaluates
96 unseen source-family examples exactly once after selection.

The only geometry generator is AssetWright's Kotlin AdvancedFormLab.
No DINO model, outside mesh generator, external text encoder or Android
deployment is involved. All output weights preserve lineage and rollback.
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
from native_studied_warm_start import DEFAULT,load_provenance,warm_start

SCHEMA="assetwright-forge-mini-native-continued-training-v4"
MODEL_SCHEMA="assetwright-original-native-continued-weights-v4"
PROPOSAL_SCHEMA="assetwright-continuing-native-proposals-v4"
SEEDS=(117,701,1601,3209)
MODES=("balanced_replay","replay_and_distill")
STEPS_TO_TEST=75
OLD_STRENGTHS=(.06,.20,.34,.50,.65,.79,.94)
PRIOR_STUDY="strength_marathon_v3"


def source_rows(fresh_manifest:dict,fresh_images:Path,
                prior_manifest:dict,prior_images:Path)->dict:
    if STUDY!="strength_continual_v4":
        raise ValueError("Missing isolated new source family study")
    new=checked_manifest(fresh_manifest,fresh_images)
    split={"train":[],"development":[],"validation":[]}
    for row in new:
        pixels=image_features(row,fresh_images)
        split[row["split"]].append({
            "case":row["case"],"family":row["family"],"op":row["operation"],
            "strength":row["strength"],"x":pixels,
            "morph":row["measured_morphology_delta"],
            "source_hash":row["modified_glb_sha256"],
            "baseline_hash":row["baseline_glb_sha256"],
            "dims":{k:row[k] for k in ("length","width","height")}
        })
    if {k:len(v) for k,v in split.items()}!={
        "train":504,"development":96,"validation":96}:
        raise ValueError("Invalid new native geometry cohort counts")
    if (prior_manifest.get("schema")!="assetwright-native-before-after-observations-v1"
        or prior_manifest.get("study_id")!=PRIOR_STUDY
        or prior_manifest.get("paired_examples")!=864
        or prior_manifest.get("source_count")!=888
        or prior_manifest.get("renderer")!="fixed-family-orthographic-clay"
        or prior_manifest.get("external_geometry_used") is not False):
        raise ValueError("Historical source replay has invalid original manifest")
    history=prior_manifest["records"]
    if not isinstance(history,list) or len(history)!=864:
        raise ValueError("Old source manifest not complete")
    historical={"train":[],"development":[]}
    seen=set();hashes=set()
    for row in history:
        phase=row["split"]
        # Prior inspected *validation* must not even be included in memory replay.
        if phase=="validation":continue
        if phase not in historical:
            raise ValueError("Unrecognized old source split")
        family=row.get("family")
        match=re.fullmatch(r"bm_(train|dev)(\d{2})",family or "")
        if match is None or (
            phase=="train" and (match.group(1)!="train"
                or int(match.group(2)) not in range(1,17))) or (
            phase=="development" and (match.group(1)!="dev"
                or int(match.group(2)) not in range(1,5))):
            raise ValueError("Untrusted old study source family or split")
        operation=row.get("operation")
        strength=row.get("strength")
        levels=OLD_STRENGTHS if phase=="train" else (.13,.37,.61,.87)
        if operation not in OPERATIONS or not any(
            type(strength) in (int,float) and abs(strength-v)<1e-5
            for v in levels):
            raise ValueError("Untrusted source strength or operation in replay")
        stem=f"{phase}__{family}__{operation.lower()}__s{round(1000*strength):03d}"
        baseline=f"{phase}__{family}__baseline"
        if row.get("case")!=stem or row.get("baseline_case")!=baseline or stem in seen:
            raise ValueError("Repeated/misnamed historical training example")
        seen.add(stem)
        original_hash=row.get("modified_glb_sha256")
        if (not isinstance(original_hash,str) or
            not re.fullmatch(r"[0-9a-f]{64}",original_hash) or
            original_hash in hashes):
            raise ValueError("Invalid old source hash")
        hashes.add(original_hash)
        for role,prefix in (("before",baseline),("after",stem)):
            files=row.get(role+"_view_files")
            image_hashes=row.get(role+"_view_sha256")
            if (not isinstance(files,dict) or not isinstance(image_hashes,dict) or
                set(files)!={"side","front_three_quarter"} or
                set(image_hashes)!=set(files)):
                raise ValueError("Historical replay image source headers invalid")
            for view in files:
                image=prior_images/(prefix+"__"+view+".png")
                if files[view]!=image.name or hash_file(image)!=image_hashes[view]:
                    raise ValueError("Old original image replay SHA mismatch")
        geometry=row.get("measured_morphology_delta")
        if (not isinstance(geometry,list) or len(geometry)!=6 or
            any(type(z) not in (float,int) or not math.isfinite(z) for z in geometry)):
            raise ValueError("Malformed historical physical morphology supervision")
        historical[phase].append({
            "case":stem,"family":family,"op":operation,"strength":strength,
            "x":image_features(row,prior_images),"morph":geometry,
            "source_hash":original_hash,
        })
    if {k:len(v) for k,v in historical.items()}!={"train":672,"development":96}:
        raise ValueError("Historical old model rehearsal is incomplete")
    if {r["source_hash"] for r in historical["train"]}&{
        r["source_hash"] for batch in split.values() for r in batch}:
        raise ValueError("Old and fresh original source mesh hashes overlap")
    if any(any(k.startswith("bm_blind") or k.startswith("bs_blind")
               or k.startswith("bdhold") for k in FAMILIES[p])
           for p in FAMILIES):
        raise ValueError("Re-used inspected historical validation sources")
    return {"fresh":split,"historical":historical}


def train(fresh:dict,prior:dict,fresh_images:Path,prior_images:Path,
          output:Path,knowledge:Path,seconds:int)->dict:
    import numpy as np
    import torch
    from torch import nn
    import torch.nn.functional as F
    from safetensors.torch import save_file
    if not 900<=seconds<=2100:
        raise ValueError("Continued optimizer budget must be 15-35 minutes")
    lineage,standard,_=load_provenance(knowledge)
    cohorts=source_rows(fresh,fresh_images,prior,prior_images)
    previous=cohorts["historical"]
    current=cohorts["fresh"]
    torch.set_num_threads(min(torch.get_num_threads(),2))
    old_train=previous["train"]
    new_train=current["train"]
    replay=old_train+new_train
    raw=np.asarray([r["x"] for r in replay],dtype=np.float32)
    center=raw.mean(axis=0)
    scale=np.maximum(raw.std(axis=0),.06)
    physical=np.asarray([r["morph"] for r in replay],dtype=np.float32)
    phys_scale=np.maximum(physical.std(axis=0),.07)
    def tensors(rows):
        if not rows:
            raise ValueError("Source family cannot be empty")
        X=(np.asarray([r["x"] for r in rows],dtype=np.float32)-center)/scale
        return (
            torch.tensor(X,dtype=torch.float32),
            torch.tensor([OPERATIONS.index(r["op"]) for r in rows],dtype=torch.long),
            torch.tensor([r["strength"] for r in rows],dtype=torch.float32),
            torch.tensor(np.asarray([r["morph"] for r in rows],dtype=np.float32)/phys_scale)
        )
    old=tensors(old_train)
    fresh_train=tensors(new_train)
    new_dev=tensors(current["development"])
    # Prior development cohort is only for retention reporting, NOT
    # hyperparameter selection: it was previously inspected.
    old_dev=tensors(previous["development"])

    class NativeStudent(nn.Module):
        def __init__(self):
            super().__init__()
            self.core=nn.Sequential(
                nn.Linear(INPUT_DIM,96),nn.Tanh(),
                nn.Linear(96,96),nn.Tanh())
            self.op=nn.Linear(96,len(OPERATIONS))
            self.strength=nn.Linear(96,len(OPERATIONS))
            self.physical=nn.Linear(96,6)
            self.dino=nn.Linear(96,24)
        def forward(self,X):
            h=self.core(X)
            return (self.op(h),torch.sigmoid(self.strength(h)),
                    self.physical(h),self.dino(h))

    def stats(model,batch):
        model.eval()
        X,ops,strengths,_=batch
        with torch.inference_mode():
            logits,powers,_,_=model(X)
            labels=logits.argmax(1)
            inferred=powers.gather(1,labels[:,None]).flatten()
            oracle=powers.gather(1,ops[:,None]).flatten()
            mae=float((inferred-strengths).abs().mean())
            ce=float(F.cross_entropy(logits,ops))
            return {
                "accuracy":float((labels==ops).float().mean()),
                "strength_mae":mae,
                "oracle_strength_mae":float((oracle-strengths).abs().mean()),
                "cross_entropy":ce,
                "dev_priority":.56*ce+3.9*mae,
                "per_operation":{
                    op:{"total":int((ops==i).sum()),
                        "correct":int(((labels==i)&(ops==i)).sum()),
                        "strength_mae":float((inferred[ops==i]-strengths[ops==i]).abs().mean())}
                    for i,op in enumerate(OPERATIONS)
                }
            }
    prior_model=NativeStudent()
    warm_details=warm_start(prior_model,center,scale,knowledge)
    # Prove the old initial checkpoint is still numerically the same
    # function on the historical training examples after normalization rebasing.
    original=NativeStudent()
    from safetensors.torch import load_file
    original.load_state_dict(load_file(str(knowledge/"owned_native_student.safetensors"),
                                   device="cpu"),strict=True)
    old_X=old[0]
    old_raw=(np.asarray([r["x"] for r in old_train],dtype=np.float32)
              -np.asarray(standard["train_feature_mean"],dtype=np.float32)
             )/np.asarray(standard["train_feature_std"],dtype=np.float32)
    with torch.inference_mode():
        old_logits=original(torch.tensor(old_raw,dtype=torch.float32))[0]
        rebased_logits=prior_model(old_X)[0]
        mean_delta=float((old_logits-rebased_logits).abs().max())
    if mean_delta>.002:
        raise ValueError("Rebasing old saved model changed its learned representations")
    # Old predicted distributions regularize future original native model.
    with torch.inference_mode():
        prior_old_logits,prior_old_heads,_,_=prior_model(old[0])
    old_dev_before=stats(prior_model,old_dev)
    new_dev_before=stats(prior_model,new_dev)
    prior_train_before=stats(prior_model,old)
    output.mkdir(parents=True,exist_ok=True)
    (output/"sessions").mkdir(exist_ok=True)
    budget=seconds/(len(SEEDS)*len(MODES))
    histories=[]
    champion_state=None
    champion_priority=float("inf")
    champion_meta=None
    active_seconds=0.
    for mode in MODES:
        for seed in SEEDS:
            torch.manual_seed(seed)
            model=NativeStudent()
            model.load_state_dict(copy.deepcopy(prior_model.state_dict()))
            optimizer=torch.optim.AdamW(model.parameters(),lr=.00042,
                                        weight_decay=.001)
            best_state=None
            best_dev=float("inf")
            best_step=0
            steps=0
            start=time.perf_counter()
            until=start+budget
            last_report=start
            while time.perf_counter()<until or steps<75:
                model.train()
                i_new=torch.randint(len(new_train),(96,))
                i_old=torch.randint(len(old_train),(64,))
                X=torch.cat((fresh_train[0][i_new],old[0][i_old]),0)
                y=torch.cat((fresh_train[1][i_new],old[1][i_old]),0)
                strengths=torch.cat((fresh_train[2][i_new],old[2][i_old]),0)
                shape=torch.cat((fresh_train[3][i_new],old[3][i_old]),0)
                progress=min(1.,(time.perf_counter()-start)/budget)
                X=X+(0.006+.005*progress)*torch.randn_like(X)
                scores,powers,morph,_=model(X)
                selected=powers.gather(1,y[:,None]).flatten()
                # Preserve existing skills AND fit new source transformations.
                loss=.9*F.cross_entropy(scores,y)
                loss+=(4.0+2.0*progress)*F.smooth_l1_loss(
                    selected,strengths,beta=.085)
                loss+=.13*F.smooth_l1_loss(morph,shape,beta=.2)
                if mode=="replay_and_distill":
                    current_logits,current_heads,_,_=model(old[0][i_old])
                    loss+=.20*F.mse_loss(current_logits,prior_old_logits[i_old])
                    loss+=.32*F.mse_loss(current_heads,prior_old_heads[i_old])
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(),2.)
                optimizer.step()
                steps+=1
                if steps%STEPS_TO_TEST==0:
                    dev=stats(model,new_dev)
                    retention=stats(model,old)
                    # Development-only selection, with old TRAIN replay
                    # evidence of retaining known skills.
                    retention_ok=(
                        retention["accuracy"]>=prior_train_before["accuracy"]-.025
                        and retention["strength_mae"]<=
                            prior_train_before["strength_mae"]+.02)
                    if retention_ok and dev["dev_priority"]<best_dev:
                        best_dev=dev["dev_priority"]
                        best_state={k:v.detach().cpu().clone()
                                    for k,v in model.state_dict().items()}
                        best_step=steps
                    now=time.perf_counter()
                    if now-last_report>=28:
                        print("CONTINUAL_OPT "+json.dumps({
                            "condition":mode,"seed":seed,"steps":steps,
                            "elapsed_seconds":round(now-start,1),
                            "dev_best":round(best_dev,7),
                            "old_rehearsal_retained":retention_ok
                        }),flush=True)
                        last_report=now
            elapsed=time.perf_counter()-start
            active_seconds+=elapsed
            # Even a failure to improve is preserved in explicit metrics,
            # but it does not overwrite previously learned weights.
            if best_state is None:
                best_state=copy.deepcopy(prior_model.state_dict())
                best_step=0
            model.load_state_dict(best_state,strict=True)
            dev=stats(model,new_dev)
            retention=stats(model,old)
            filename=f"{mode}__seed_{seed}.safetensors"
            save_file({k:v.detach().cpu().contiguous()
                       for k,v in model.state_dict().items()},
                      output/"sessions"/filename)
            meta={
                "mode":mode,"seed":seed,"active_training_seconds":round(elapsed,3),
                "optimizer_updates":steps,"selected_development_step":best_step,
                "selected_on_new_development_only":True,
                "source_replay_examples_per_batch":64,
                "new_source_examples_per_batch":96,
                "new_development":dev,"old_training_retention":retention,
                "checkpoint_file":filename
            }
            histories.append(meta)
            if best_step>0 and dev["dev_priority"]<champion_priority:
                champion_priority=dev["dev_priority"]
                champion_state=copy.deepcopy(best_state)
                champion_meta={"seed":seed,"mode":mode,"filename":filename,
                               "selected_step":best_step}
            print("CONTINUAL_SESSION "+json.dumps({
                "mode":mode,"seed":seed,"elapsed":round(elapsed,1),
                "updates":steps,"selected_step":best_step,
                "dev":dev["dev_priority"]
            }),flush=True)
    if active_seconds<seconds:
        raise ValueError("Insufficient real neural gradient training time")
    if champion_state is None:
        raise ValueError("No new model passed old-training retention")
    candidate=NativeStudent()
    candidate.load_state_dict(champion_state,strict=True)
    # The blind source split is never materialized until all candidate
    # selection is FINISHED; no seed or recipe sees it.
    blind=tensors(current["validation"])
    frozen={"prior":prior_model,"continued":candidate}
    heldout={label:stats(model,blind) for label,model in frozen.items()}
    old_dev_after=stats(candidate,old_dev)
    old_train_after=stats(candidate,old)
    blind_sha=hashlib.sha256("\n".join(sorted(
        row["source_hash"] for row in current["validation"])).encode()).hexdigest()
    replay_sha=hashlib.sha256("\n".join(sorted(
        row["source_hash"] for row in old_train)).encode()).hexdigest()
    gain=(heldout["prior"]["strength_mae"]-
          heldout["continued"]["strength_mae"])/heldout["prior"]["strength_mae"]
    results={
        "schema":SCHEMA,"study":"strength_continual_v4",
        "old_prior_saved_hash":lineage["saved_weights_sha256"],
        "warm_start_verified_from_original":True,
        "rebased_max_logit_difference":mean_delta,
        "prior_training_sources_rehearsed":672,
        "prior_development_retention_examples":96,
        "historical_validation_leaked_into_training":False,
        "new_training_examples":504,
        "new_development_examples":96,
        "new_unseen_validation_examples":96,
        "old_rehearsal_hash":replay_sha,
        "new_blind_original_mesh_hash":blind_sha,
        "measured_training_seconds":round(active_seconds,3),
        "configured_training_seconds":seconds,
        "training_sessions_completed":len(histories),
        "sessions":histories,
        "selected_candidate":champion_meta,
        "new_dev_prior":new_dev_before,
        "new_dev_candidate":stats(candidate,new_dev),
        "old_train_prior":prior_train_before,
        "old_train_candidate":old_train_after,
        "old_dev_prior_retrospective":old_dev_before,
        "old_dev_candidate_retrospective":old_dev_after,
        "new_blind":heldout,
        "heldout_strength_gain_vs_retained_prior_fraction":gain,
        "teacher_used_in_this_training":False,
        "external_AI_created_meshes":False,
        "androiD_checkpoint_installed":False,
        "automatic_production_promotion":False,
        "actual_Kotlin_reconstruction_pending":True
    }
    save_file({k:v.detach().cpu().contiguous()
               for k,v in candidate.state_dict().items()},
              output/"continued_candidate.safetensors")
    proposal={"schema":PROPOSAL_SCHEMA,
              "original_blind_hashes":blind_sha,"external_mesh_used":False,
              "prior":[],"continued":[]}
    for label,model in frozen.items():
        model.eval()
        with torch.inference_mode():
            scores,heads,_,_=model(blind[0])
            idx=scores.argmax(1)
            power=heads.gather(1,idx[:,None]).flatten()
        for i,row in enumerate(current["validation"]):
            proposal[label].append({
                "case":row["case"],
                "source_glb_sha256":row["source_hash"],
                "baseline_glb_sha256":row["baseline_hash"],
                "predicted_operation":OPERATIONS[int(idx[i])],
                "predicted_strength":round(float(power[i]),7),
                **row["dims"]
            })
    (output/"evaluation.json").write_text(json.dumps(results,indent=2)+"\n")
    (output/"predictions.json").write_text(json.dumps(proposal,indent=2)+"\n")
    source_lines=["schema="+PROPOSAL_SCHEMA,"external_mesh_used=false","count=96"]
    for variant in ("prior","continued"):
        for i,row in enumerate(proposal[variant]):
            for k,v in row.items():
                source_lines.append(f"{variant}.{i}.{k}={v}")
    (output/"native_proposals.properties").write_text("\n".join(source_lines)+"\n")
    (output/"candidate_lineage.json").write_text(json.dumps({
        "schema":MODEL_SCHEMA,
        "parent_source_checkpoint_sha256":lineage["saved_weights_sha256"],
        "previous_training_run":lineage["research_run_id"],
        "previous_model_weight_count":lineage["parameter_count"],
        "previous_stored_model_reloaded":True,
        "old_training_replay_samples":672,
        "fresh_new_training_samples":504,
        "model_architecture":"owned-2layer-96-native-operator-strength-pixel-student",
        "new_train_feature_mean":center.tolist(),
        "new_train_feature_std":scale.tolist(),
        "new_train_morph_std":phys_scale.tolist(),
        "fresh_validation_hash":blind_sha,
        "selected_on_fresh_development_only":True,
        "teacher_required_at_inference":False,
        "android_deployable":False,
        "human_review_required":True,
        "learning_is_cumulative":True
    },separators=(",",":"))+"\n")
    print("CONTINUAL_LEARNING_COMPLETED "+json.dumps({
        "actual_gradient_seconds":round(active_seconds,1),
        "parent_weight_sha256":lineage["saved_weights_sha256"],
        "winner":champion_meta,
        "new_blind_metrics":heldout,
        "rehearsal_accuracy_before":prior_train_before["accuracy"],
        "rehearsal_accuracy_after":old_train_after["accuracy"],
        "android_deployable":False,
    }),flush=True)
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("new_manifest","new_images","prior_manifest","prior_images",
                 "out","knowledge"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    p.add_argument("--training-seconds",type=int,default=1920)
    a=p.parse_args()
    train(json.loads(a.new_manifest.read_text()),
          json.loads(a.prior_manifest.read_text()),
          a.new_images,a.prior_images,a.out,a.knowledge,a.training_seconds)


if __name__=="__main__":
    main()

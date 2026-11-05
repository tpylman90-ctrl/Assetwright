"""Forge Mini v5: geometry-weighted CONTINUAL neural learning and mistake mining.

Equal-CPU-budget, same checkpoint, same TRAINING sources in three arms:
(1) balanced replay-only control, (2) true indexed Kotlin 3D vertex
supervision, (3) geometry supervision plus adaptive supervised hard mining.

672 historical original examples + 504 valid unpromoted v4 examples are
REPLAYED with 504 newly generated v5 examples. 96 additional v5 cases
select checkpoint and method, and 96 FRESH sealed v5 cases are tested
only once after ALL decisions. 384 actual native GLBs are independently
reconstructed for full-geometry evaluation.
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
from dino_delta_student import image_features,INPUT_DIM
from native_studied_warm_start import DEFAULT,load_provenance,warm_start
from native_vertex_supervision import prepare,proxy_loss,difficulty_scores

SCHEMA="assetwright-geometry-aware-continuation-evaluation-v5"
MODEL_SCHEMA="assetwright-original-geometry-aware-trained-weights-v5"
PROPOSAL_SCHEMA="assetwright-geometry-aware-native-proposals-v5"
CONDITIONS=("replay_only","geometry_supervised","geometry_hard_mining")
VARIANTS=("prior",)+CONDITIONS
SEEDS=(191,1601)
SELECT_EVERY=100
PRIOR_DETAILS={
    "strength_marathon_v3":{
        "count":864,"train":672,"development":96,"family_prefix":"bm_train",
        "train_levels":(.06,.20,.34,.50,.65,.79,.94)
    },
    "strength_continual_v4":{
        "count":696,"train":504,"development":96,"family_prefix":"bc_train",
        "train_levels":(.03,.18,.36,.52,.68,.83,.97)
    },
}


def old_replay(manifest:dict,images:Path,source:Path,study:str)->list[dict]:
    details=PRIOR_DETAILS[study]
    if not (
        manifest.get("schema")=="assetwright-native-before-after-observations-v1"
        and manifest.get("study_id")==study
        and manifest.get("generator")=="AssetWright-Kotlin-AdvancedFormLab"
        and manifest.get("external_geometry_used") is False
        and manifest.get("paired_examples")==details["count"]
        and len(manifest.get("records",[]))==details["count"]
        and manifest.get("source_count")==details["count"]+(
            24 if study=="strength_marathon_v3" else 20)):
        raise ValueError("Prior TRAINING study identity/provenance changed")
    rows=[];seen=set();digests=set()
    for item in manifest["records"]:
        # Never train on older inspected validation AND development splits.
        if item.get("split")!="train":
            continue
        family=item.get("family")
        op=item.get("operation")
        strength=item.get("strength")
        if (not isinstance(family,str)
            or not re.fullmatch(details["family_prefix"]+r"\d{2}",family)
            or int(family[-2:]) not in range(
                1,17 if study=="strength_marathon_v3" else 13)
            or op not in OPERATIONS or type(strength) not in (float,int)
            or not any(abs(strength-x)<1e-6 for x in details["train_levels"])):
            raise ValueError("Historical TRAINING shape not source-disjoint or labeled")
        stem=f"train__{family}__{op.lower()}__s{round(strength*1000):03d}"
        baseline=f"train__{family}__baseline"
        expected_hash=item.get("modified_glb_sha256")
        base_hash=item.get("baseline_glb_sha256")
        if (item.get("case")!=stem or item.get("baseline_case")!=baseline
            or stem in seen or not isinstance(expected_hash,str)
            or not re.fullmatch(r"[0-9a-f]{64}",expected_hash)
            or not isinstance(base_hash,str)
            or not re.fullmatch(r"[0-9a-f]{64}",base_hash)
            or expected_hash in digests):
            raise ValueError("Historical source hashes are repeated/altered")
        seen.add(stem);digests.add(expected_hash)
        if (hash_file(source/(stem+".glb"))!=expected_hash or
            hash_file(source/(baseline+".glb"))!=base_hash):
            raise ValueError("Previous original Kotlin GLB source SHA mismatch")
        for role,prefix in (("before",baseline),("after",stem)):
            names=item.get(role+"_view_files",{})
            hashes=item.get(role+"_view_sha256",{})
            if set(names)!={"side","front_three_quarter"} or set(hashes)!=set(names):
                raise ValueError("Historical aligned pixel inputs incomplete")
            for view in names:
                image=images/(prefix+"__"+view+".png")
                if names[view]!=image.name or hashes[view]!=hash_file(image):
                    raise ValueError("Historical image hashes changed")
        morphology=item.get("measured_morphology_delta")
        if (not isinstance(morphology,list) or len(morphology)!=6 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in morphology)):
            raise ValueError("Previous source native morphology unbounded")
        dims={k:item[k] for k in ("length","width","height")}
        rows.append({
            "case":stem,"split":"train","family":family,
            "op":op,"strength":strength,"x":image_features(item,images),
            "morph":morphology,"source_hash":expected_hash,
            "baseline_hash":base_hash,"dims":dims
        })
    if len(rows)!=details["train"]:
        raise ValueError("Incomplete earlier approved source replay curriculum")
    return rows


def fresh_rows(manifest:dict,images:Path)->dict:
    if STUDY!="geometry_aware_v5":
        raise ValueError("Expected source-disjoint new v5 family curriculum")
    aligned=checked_manifest(manifest,images)
    partition={"train":[],"development":[],"validation":[]}
    for item in aligned:
        phase=item["split"]
        partition[phase].append({
            "case":item["case"],"split":phase,"family":item["family"],
            "op":item["operation"],"strength":item["strength"],
            "x":image_features(item,images),
            "morph":item["measured_morphology_delta"],
            "source_hash":item["modified_glb_sha256"],
            "baseline_hash":item["baseline_glb_sha256"],
            "dims":{k:item[k] for k in ("length","width","height")}
        })
    if {k:len(v) for k,v in partition.items()}!={
        "train":504,"development":96,"validation":96}:
        raise ValueError("Fresh v5 original native cohort incomplete")
    if any(set(FAMILIES[a])&set(FAMILIES[b])
           for a,b in (("train","development"),("train","validation"),
                       ("development","validation"))):
        raise ValueError("Source family split leaked")
    for key in FAMILIES:
        if not all(f.startswith("bg_") for f in FAMILIES[key]):
            raise ValueError("Inspected historical validation family reused")
    old_hashes=set()
    for rows in partition.values():
        for item in rows:
            if item["source_hash"] in old_hashes:
                raise ValueError("Duplicate new source GLB hash")
            old_hashes.add(item["source_hash"])
    return partition


def train(new_manifest:dict,new_images:Path,new_source:Path,
          old_v3_manifest:dict,old_v3_images:Path,old_v3_source:Path,
          old_v4_manifest:dict,old_v4_images:Path,old_v4_source:Path,
          knowledge:Path,output:Path,active_seconds:int)->dict:
    import numpy as np
    import torch
    from torch import nn
    import torch.nn.functional as F
    from safetensors.torch import save_file,load_file
    if not 1200<=active_seconds<=2400:
        raise ValueError("Active geometry-aware optimizer must run for 20-40 minutes")
    lineage,normalization,_=load_provenance(knowledge)
    v3=old_replay(old_v3_manifest,old_v3_images,old_v3_source,"strength_marathon_v3")
    v4=old_replay(old_v4_manifest,old_v4_images,old_v4_source,"strength_continual_v4")
    current=fresh_rows(new_manifest,new_images)
    known=v3+v4
    novel=current["train"]
    if (len(known),len(novel))!=(1176,504):
        raise ValueError("All prior real native geometry lessons must be replayed")
    if {r["source_hash"] for r in known}&{
        r["source_hash"] for phase in current.values() for r in phase}:
        raise ValueError("Old and fresh native GLBs are not disjoint")
    # Ground truth indexed vertices are training SUPERVISION ONLY. They are
    # never introduced as model input or used for heldout hyperparameters.
    geom3=prepare(v3,old_v3_source)
    geom4=prepare(v4,old_v4_source)
    geom_new=prepare(novel,new_source)
    geom_dev=prepare(current["development"],new_source)
    old_targets=np.concatenate((geom3["targets"],geom4["targets"]),axis=0)
    old_basis=np.concatenate((geom3["basis"],geom4["basis"]),axis=0)
    geo_sha=hashlib.sha256(
        "\n".join(sorted([geom3["source_digests_sha256"],
                         geom4["source_digests_sha256"],
                         geom_new["source_digests_sha256"]])).encode()).hexdigest()
    torch.set_num_threads(min(torch.get_num_threads(),2))
    entire=known+novel
    pixels=np.asarray([row["x"] for row in entire],dtype=np.float32)
    center=pixels.mean(axis=0)
    std=np.maximum(pixels.std(axis=0),.06)
    morph=np.asarray([row["morph"] for row in entire],dtype=np.float32)
    morph_scale=np.maximum(morph.std(axis=0),.07)
    def make_batch(rows,basis,targets):
        inputs=(np.asarray([r["x"] for r in rows],dtype=np.float32)-center)/std
        return (
            torch.tensor(inputs,dtype=torch.float32),
            torch.tensor([OPERATIONS.index(r["op"]) for r in rows],dtype=torch.long),
            torch.tensor([r["strength"] for r in rows],dtype=torch.float32),
            torch.tensor(np.asarray([r["morph"] for r in rows],dtype=np.float32)
                         /morph_scale,dtype=torch.float32),
            torch.tensor(basis,dtype=torch.float32),
            torch.tensor(targets,dtype=torch.float32)
        )
    old=make_batch(known,old_basis,old_targets)
    new=make_batch(novel,geom_new["basis"],geom_new["targets"])
    dev=make_batch(current["development"],geom_dev["basis"],geom_dev["targets"])
    class NativeStudent(nn.Module):
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

    def evaluate(model,batch):
        model.eval()
        with torch.inference_mode():
            scores,heads,_,_=model(batch[0])
            op=batch[1];truth=batch[2]
            predicted=scores.argmax(1)
            power=heads.gather(1,predicted[:,None]).flatten()
            ce=float(F.cross_entropy(scores,op))
            mae=float((power-truth).abs().mean())
            basis=batch[4];Y=batch[5]
            idx=torch.arange(len(op))
            # DEV physical proxy scores the SAME discrete class and strength
            # that the original Kotlin engine will ultimately execute.
            shape=basis[idx,predicted,:]*power[:,None]
            physical_rmse=float(torch.sqrt(((shape-Y)**2).mean()))
            return {
                "operation_accuracy":float((predicted==op).float().mean()),
                "strength_mae":mae,
                "operator_cross_entropy":ce,
                "matched_native_vertex_proxy_rmse":physical_rmse,
                "selection_priority":.52*ce+3.6*mae+30.*physical_rmse
            }

    prior=NativeStudent()
    warm=warm_start(prior,center,std,knowledge)
    # Confirm analytic rebasing really preserves original source predictions.
    raw_old=(np.asarray([row["x"] for row in known],dtype=np.float32)
            -np.asarray(normalization["train_feature_mean"],dtype=np.float32)) \
            /np.asarray(normalization["train_feature_std"],dtype=np.float32)
    original=NativeStudent()
    original.load_state_dict(
        load_file(str(knowledge/"owned_native_student.safetensors"),device="cpu"),
        strict=True)
    with torch.inference_mode():
        diff=float((prior(old[0])[0]-original(
            torch.tensor(raw_old,dtype=torch.float32))[0]).abs().max())
    if diff>.002:
        raise ValueError("Saved original Mini AI skill changed during normalization")
    parent_old=evaluate(prior,old)
    parent_dev=evaluate(prior,dev)
    with torch.inference_mode():
        old_logits,old_heads,_,_=prior(old[0])

    output.mkdir(parents=True,exist_ok=True)
    session_dir=output/"sessions";session_dir.mkdir(exist_ok=True)
    winner_dir=output/"winners";winner_dir.mkdir(exist_ok=True)
    duration=active_seconds/(len(CONDITIONS)*len(SEEDS))
    sessions=[]
    champions={}
    selected={}
    budget_actual=0.
    for condition in CONDITIONS:
        best_priority=float("inf")
        best_state=None
        best_info=None
        for seed in SEEDS:
            torch.manual_seed(seed)
            model=NativeStudent()
            model.load_state_dict(copy.deepcopy(prior.state_dict()),strict=True)
            opt=torch.optim.AdamW(model.parameters(),lr=.00036,
                                  weight_decay=.0009)
            old_mining=torch.full((len(known),),1/len(known))
            new_mining=torch.full((len(novel),),1/len(novel))
            saved=None;score_best=float("inf")
            selected_step=0;steps=0
            begin=time.perf_counter()
            until=begin+duration
            last_log=begin
            while time.perf_counter()<until or steps<SELECT_EVERY:
                model.train()
                if condition=="geometry_hard_mining":
                    sample_old=torch.multinomial(old_mining,64,replacement=True)
                    sample_new=torch.multinomial(new_mining,96,replacement=True)
                else:
                    sample_old=torch.randint(len(known),(64,))
                    sample_new=torch.randint(len(novel),(96,))
                X=torch.cat((new[0][sample_new],old[0][sample_old]),0)
                op=torch.cat((new[1][sample_new],old[1][sample_old]),0)
                power=torch.cat((new[2][sample_new],old[2][sample_old]),0)
                morph=torch.cat((new[3][sample_new],old[3][sample_old]),0)
                basis=torch.cat((new[4][sample_new],old[4][sample_old]),0)
                targets=torch.cat((new[5][sample_new],old[5][sample_old]),0)
                X=X+.008*torch.randn_like(X)
                logits,heads,shape,_=model(X)
                inferred=heads.gather(1,op[:,None]).flatten()
                loss=.9*F.cross_entropy(logits,op)
                loss+=5.0*F.smooth_l1_loss(inferred,power,beta=.09)
                loss+=.10*F.smooth_l1_loss(shape,morph,beta=.2)
                if condition!="replay_only":
                    loss+=proxy_loss(logits,heads,basis,targets,op)
                # All arms have the SAME old-learning retention penalty.
                remembered_scores,remembered_heads,_,_=model(old[0][sample_old])
                loss+=.15*F.mse_loss(remembered_scores,old_logits[sample_old])
                loss+=.18*F.mse_loss(remembered_heads,old_heads[sample_old])
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(),2.)
                opt.step()
                steps+=1
                if condition=="geometry_hard_mining" and steps%250==0:
                    model.eval()
                    with torch.no_grad():
                        def priorities(data):
                            scores,heads,_,_=model(data[0])
                            errors=difficulty_scores(scores,heads,data[1],data[2])
                            z=(errors-errors.mean())/(errors.std()+1.e-6)
                            # Real correct labels only. 40% uniform floor
                            # prevents easy operations from disappearing.
                            p=.40/len(errors)+.60*torch.softmax(
                                z.clamp(-3,3),dim=0)
                            return p.detach()
                        new_mining=priorities(new)
                        old_mining=priorities(old)
                if steps%SELECT_EVERY==0:
                    developmental=evaluate(model,dev)
                    retention=evaluate(model,old)
                    retained=(
                        retention["operation_accuracy"]>=
                            parent_old["operation_accuracy"]-.018
                        and retention["strength_mae"]<=
                            parent_old["strength_mae"]+.014
                    )
                    if retained and developmental["selection_priority"]<score_best:
                        score_best=developmental["selection_priority"]
                        saved={k:v.detach().cpu().clone()
                               for k,v in model.state_dict().items()}
                        selected_step=steps
                    now=time.perf_counter()
                    if now-last_log>27:
                        print("GEOMETRY_TRAINING "+json.dumps({
                            "condition":condition,"seed":seed,
                            "elapsed_optimizer_seconds":round(now-begin,2),
                            "updates":steps,"retains_previous_training":retained,
                            "best_fresh_dev_priority":round(score_best,6)
                        }),flush=True)
                        last_log=now
            measured=time.perf_counter()-begin
            budget_actual+=measured
            if saved is None:
                saved=copy.deepcopy(prior.state_dict())
                selected_step=0
            model.load_state_dict(saved,strict=True)
            development=evaluate(model,dev)
            old_report=evaluate(model,old)
            file=session_dir/(condition+"__"+str(seed)+".safetensors")
            save_file({k:v.detach().cpu().contiguous()
                       for k,v in model.state_dict().items()},file)
            session={
                "condition":condition,"seed":seed,
                "actual_optimizer_seconds":round(measured,3),
                "gradient_updates":steps,
                "selected_fresh_development_step":selected_step,
                "fresh_development":development,
                "old_source_replay_retention":old_report,
                "weights":file.name
            }
            sessions.append(session)
            if selected_step and developmental["selection_priority"]<float("inf"):
                if development["selection_priority"]<best_priority:
                    best_priority=development["selection_priority"]
                    best_state=copy.deepcopy(saved)
                    best_info={"condition":condition,"seed":seed,
                               "selected_step":selected_step}
            print("GEOMETRY_SESSION_DONE "+json.dumps({
                "condition":condition,"seed":seed,
                "actual_seconds":round(measured,3),
                "gradient_updates":steps,
                "selected_step":selected_step,
                "dev_priority":development["selection_priority"]
            }),flush=True)
        if best_state is None:
            raise ValueError("No checkpoint maintained genuine earlier model skill")
        champion=NativeStudent()
        champion.load_state_dict(best_state,strict=True)
        champions[condition]=champion
        selected[condition]=best_info
        save_file({k:v.detach().cpu().contiguous()
                   for k,v in champion.state_dict().items()},
                  winner_dir/(condition+".safetensors"))
    if budget_actual<active_seconds:
        raise ValueError("Insufficient measured physical CPU optimizer time")
    # Only NEW development can select preferred method, never heldout.
    dev_scores={key:evaluate(value,dev) for key,value
                in [("prior",prior)]+list(champions.items())}
    leader=min(CONDITIONS,key=lambda key:dev_scores[key]["selection_priority"])

    # Strictly ONE blind evaluation, after every seed, epoch and METHOD
    # is selected. Neither supervised geometry nor hard mining sees it.
    blind=current["validation"]
    blind_X=(np.asarray([x["x"] for x in blind],dtype=np.float32)-center)/std
    blind_tensor=torch.tensor(blind_X,dtype=torch.float32)
    models={"prior":prior,**champions}
    results={}
    proposals={
        "schema":PROPOSAL_SCHEMA,
        "external_mesh_used":False,
        "count":96,
        "blind_study":"geometry_aware_v5",
        "prior":[],
        "replay_only":[],
        "geometry_supervised":[],
        "geometry_hard_mining":[]
    }
    for name,model in models.items():
        model.eval()
        with torch.inference_mode():
            scores,powers,_,_=model(blind_tensor)
            classes=scores.argmax(1)
            estimated=powers.gather(1,classes[:,None]).flatten()
            results[name]={
                "operation_accuracy":float((
                    classes==torch.tensor([
                        OPERATIONS.index(x["op"]) for x in blind])).float().mean()),
                "strength_mae":float((estimated-torch.tensor([
                    x["strength"] for x in blind])).abs().mean()),
                "per_operation":{
                    op:{
                        "count":sum(x["op"]==op for x in blind),
                        "correct":sum(
                            int(classes[i])==OPERATIONS.index(op)
                            for i,x in enumerate(blind) if x["op"]==op)
                    } for op in OPERATIONS
                }
            }
        for i,row in enumerate(blind):
            proposals[name].append({
                "case":row["case"],
                "source_glb_sha256":row["source_hash"],
                "baseline_glb_sha256":row["baseline_hash"],
                "predicted_operation":OPERATIONS[int(classes[i])],
                "predicted_strength":round(float(estimated[i]),7),
                **row["dims"]
            })
    blind_digest=hashlib.sha256("\n".join(sorted(
        row["source_hash"] for row in blind)).encode()).hexdigest()
    old_digest=hashlib.sha256("\n".join(sorted(
        row["source_hash"] for row in known)).encode()).hexdigest()
    report={
        "schema":SCHEMA,"study":"geometry_aware_v5",
        "starting_learned_checkpoint_sha256":lineage["saved_weights_sha256"],
        "retained_old_network_was_reloaded":True,
        "normalization_rebase_max_prediction_error":diff,
        "real_Kotlin_prior_training_GLBS_replayed":1176,
        "earlier_v3_source_examples":672,
        "earlier_v4_failed_candidate_correct_source_examples":504,
        "new_v5_training_examples":504,
        "new_v5_development_examples":96,
        "new_v5_blind_examples":96,
        "heldout_not_in_any_model_selection":True,
        "source_replay_digest":old_digest,
        "actual_3d_geometry_supervision_digest":geo_sha,
        "sampled_native_vertices_per_training_target":64,
        "actual_training_optimizer_seconds":round(budget_actual,3),
        "required_optimizer_seconds":active_seconds,
        "completed_independent_sessions":len(sessions),
        "same_original_start_all_conditions":True,
        "same_training_data_and_cpu_budget":True,
        "condition_seeds":list(SEEDS),
        "session_provenance":sessions,
        "development_selected":selected,
        "fresh_development_model_comparison":dev_scores,
        "chosen_method_from_development_only":leader,
        "retained_old_training_before":parent_old,
        "retained_old_training_after":{
            name:evaluate(model,old) for name,model in champions.items()
        },
        "blind_original_GLBS_digest":blind_digest,
        "fresh_blind_results":results,
        "original_Kotlin_GLBS_reconstructed_yet":False,
        "outside_pretrained_model_used":False,
        "outside_mesh_generation_used":False,
        "android_deployed":False
    }
    model_lineage={
        "schema":MODEL_SCHEMA,"parent_sha256":lineage["saved_weights_sha256"],
        "source_original_run":lineage["research_run_id"],
        "input_dim":INPUT_DIM,"hidden_dim":96,
        "operation_names":list(OPERATIONS),
        "input_mean":center.tolist(),"input_std":std.tolist(),
        "morph_std":morph_scale.tolist(),
        "model_weights_dir":"winners",
        "original_native_3D_loss":"sampled 64 corresponding original vertex positions per source",
        "child_selected_by_development_only":leader,
        "blind_source_sha256":blind_digest,
        "validation_family_untouched_until_frozen":True,
        "approved_for_android":False,
        "human_visual_review_required":True
    }
    (output/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (output/"lineage.json").write_text(json.dumps(model_lineage,separators=(",",":"))+"\n")
    (output/"predictions.json").write_text(json.dumps(proposals,indent=2)+"\n")
    lines=[
        "schema="+PROPOSAL_SCHEMA,"external_mesh_used=false",
        "blind_study=geometry_aware_v5","count=96"
    ]
    for variant in VARIANTS:
        for idx,item in enumerate(proposals[variant]):
            for key,value in item.items():
                lines.append(f"{variant}.{idx}.{key}={value}")
    (output/"native_proposals.properties").write_text("\n".join(lines)+"\n")
    print("REAL_NATIVE_GEOMETRY_SUPERVISED_TRAINING_COMPLETE "+json.dumps({
        "active_training_seconds":round(budget_actual,2),
        "reloaded_previously_trained_sha":lineage["saved_weights_sha256"],
        "replayed_native_training_cases":1176,
        "new_native_training_cases":504,
        "development_preferred_method":leader,
        "blind_results":results,
        "new_Kotlin_GLB_validation_next":True,
        "android_deployed":False
    }),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("new_manifest","new_images","new_source",
                 "v3_manifest","v3_images","v3_source",
                 "v4_manifest","v4_images","v4_source",
                 "knowledge","out"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    p.add_argument("--training-seconds",type=int,default=1800)
    a=p.parse_args()
    train(
        json.loads(a.new_manifest.read_text()),a.new_images,a.new_source,
        json.loads(a.v3_manifest.read_text()),a.v3_images,a.v3_source,
        json.loads(a.v4_manifest.read_text()),a.v4_images,a.v4_source,
        a.knowledge,a.out,a.training_seconds
    )


if __name__=="__main__":
    main()

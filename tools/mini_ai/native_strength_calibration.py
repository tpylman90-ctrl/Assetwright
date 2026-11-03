"""Separate the owned native operation classifier from strength calibration.

Resume verified ORIGINAL AssetWright weights. Freeze the classification head
exactly; improve only strength parameters using exact native-control lessons.
Choose checkpoints using development examples, evaluate a NEW blind curriculum
once, and reject if retention or real native geometry provenance fails.

Nothing downloaded (CAD programs, teacher AI meshes, or DINOv2) generates GLBs.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random

from native_operation_intent_student import (
    OPERATIONS, SCHEMA as MODEL_SCHEMA, examples, forward, infer, text_features,
)
from native_skill_clinic import (
    validate_model, validate_proof, validate_curriculum,
)

SCHEMA="assetwright-owned-frozen-operation-strength-calibration-v2"
BLIND_SCHEMA="assetwright-native-strength-blind-v2"
GATE={
    "minimum_blind_operator_accuracy":.75,
    "minimum_blind_strength_improvement":.02,
    "maximum_blind_conditional_strength_mae":.17,
    "maximum_prior_strength_regression":.02,
    "minimum_blind_monotonic_fraction":.70,
}
SCALE=(("gentle",.30),("moderate",.60),("aggressive",.90))

def checksum(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def new_blind_rows(doc:dict)->list[dict]:
    if (doc.get("schema")!=BLIND_SCHEMA or
        doc.get("license")!="original-assetwright-authored" or
        doc.get("split")!="blind_only"):
        raise ValueError("Untrusted fresh blind evaluation source")
    templates=doc.get("templates")
    if not isinstance(templates,list) or len(templates)!=12:
        raise ValueError("Expected 12 immutable blind template groups")
    if doc.get("intensities")!=[{"word":w,"strength":v} for w,v in SCALE]:
        raise ValueError("Misaligned blind strength labels")
    used=set()
    rows=[]
    for i,record in enumerate(templates):
        if not isinstance(record,dict) or set(record)!={"operation","template"}:
            raise ValueError("Malformed blind construction lesson")
        operation=record["operation"]
        template=record["template"]
        if (operation not in OPERATIONS or not isinstance(template,str) or
            not 10<len(template)<280 or template.count("{vehicle}")!=1 or
            template.count("{level}")!=1 or template.lower() in used):
            raise ValueError("Duplicate, unsupported or ambiguous blind lesson")
        used.add(template.lower())
        for word,level in SCALE:
            prompt=template.format(vehicle="cargo-hover hauler",level=word)
            rows.append({"prompt":prompt,"operation":operation,"strength":level,
                        "source_group":f"new-blind-2026-11:template_{i}",
                        "source_kind":"independently_authored_native_gold",
                        "split":"blind"})
    if {r["operation"] for r in rows}!=set(OPERATIONS):
        raise ValueError("Blind missing native operations")
    return rows

def split_integrity(train:list[dict],dev:list[dict],blind:list[dict],
                    retained:list[dict],past_blind:list[dict])->dict:
    def unique(rows):
        prompts=[r["prompt"].strip().lower() for r in rows]
        if len(prompts)!=len(set(prompts)):
            raise ValueError("Repeated source prompt")
        return set(prompts)
    names={k:unique(v) for k,v in
           (("train",train),("development",dev),("new_blind",blind),
            ("prior_holdout",retained),("past_clinic_blind",past_blind))}
    for group in ("development","new_blind","prior_holdout","past_clinic_blind"):
        if names["train"]&names[group]:
            raise ValueError("Training leaks into "+group)
    if names["development"]&names["new_blind"]:
        raise ValueError("New blind reused for checkpoint selection")
    if names["past_clinic_blind"]&names["new_blind"]:
        raise ValueError("Previous exposed blind overlaps fresh test")
    return {"train_unique":len(names["train"]),
            "development_unique":len(names["development"]),
            "new_blind_unique":len(names["new_blind"]),
            "past_exposed_blind_excluded":True,
            "new_blind_used_for_checkpoint_selection":False}

def measure(model:dict,rows:list[dict])->dict:
    if not rows:raise ValueError("No samples to evaluate")
    correct=0
    abstained=0
    error=0.
    groups={}
    for row in rows:
        probs,heads=forward(model,row["prompt"])
        gold_idx=OPERATIONS.index(row["operation"])
        strength=heads[gold_idx]
        error+=abs(strength-row["strength"])
        guess=infer(model,row["prompt"])
        if guess["status"]=="abstain":
            abstained+=1
        else:
            correct+=guess["operation"]==row["operation"]
        groups.setdefault(row["source_group"],[]).append(
            (row["strength"],strength))
    monotonic=0
    eligible=0
    for group in groups.values():
        pairs=sorted(group)
        if len(pairs)==3 and [q[0] for q in pairs]==[.30,.60,.90]:
            eligible+=1
            monotonic+=int(pairs[0][1]<pairs[1][1]<pairs[2][1])
    return {
        "samples":len(rows),
        "operator_accuracy":round(correct/len(rows),6),
        "abstentions":abstained,
        "conditional_strength_mae":round(error/len(rows),6),
        "monotonic_strength_fraction":round(monotonic/eligible,6) if eligible else None,
        "monotonic_groups":eligible,
        "note":"Strength MAE conditions on gold operation; classifier errors separately counted."
    }

def frozen_classifier(earlier:dict,later:dict)->bool:
    return (earlier["class_weights"]==later["class_weights"] and
            earlier["class_bias"]==later["class_bias"] and
            earlier["operations"]==later["operations"])

def calibrate(model:dict,corrections:list[dict],development:list[dict],
              previous:list[dict],epochs:int=52)->tuple[dict,dict]:
    if not 1<=epochs<=80:raise ValueError("Unbounded calibration")
    pre=measure(model,previous)
    dev_start=measure(model,development)
    current=copy.deepcopy(model)
    best=copy.deepcopy(model)
    best_loss=dev_start["conditional_strength_mae"]
    checkpoint=0
    # Corrective examples and original approved labels, never unapproved
    # model outputs. Old replay is necessary to prevent forgetting strengths.
    base=examples("train")
    work=base+corrections+corrections
    cached=[(r, text_features(r["prompt"])) for r in work]
    rng=random.Random(1708)
    history=[]
    for epoch in range(1,epochs+1):
        rng.shuffle(cached)
        lr=.052/(1+.035*epoch)
        for record,x in cached:
            gold=OPERATIONS.index(record["operation"])
            _,heads=forward(current,record["prompt"])
            delta=heads[gold]-record["strength"]
            current["strength_bias"][gold]-=lr*.20*delta
            for i,value in x.items():
                current["strength_weights"][gold][i]-=lr*(
                    delta*value+.00005*current["strength_weights"][gold][i])
        if epoch%4==0 or epoch==epochs:
            dev=measure(current,development)
            old=measure(current,previous)
            history.append({"epoch":epoch,"dev_mae":dev["conditional_strength_mae"],
                            "old_mae":old["conditional_strength_mae"]})
            if (dev["conditional_strength_mae"]<best_loss-.0003 and
                old["conditional_strength_mae"]<=
                pre["conditional_strength_mae"]+GATE["maximum_prior_strength_regression"]):
                best=copy.deepcopy(current)
                best_loss=dev["conditional_strength_mae"]
                checkpoint=epoch
    if not frozen_classifier(model,best):
        raise ValueError("Attempt to modify frozen operation classifier")
    best["strength_calibration_source"]="verified-original-native-student"
    best["strength_calibration_epoch"]=checkpoint
    best["android_deployable"]=False
    best["approved_for_geometry_generation"]=False
    return best,{"initial_development_mae":dev_start["conditional_strength_mae"],
                 "selected_development_mae":best_loss,
                 "selected_epoch":checkpoint,
                 "correction_lessons":len(corrections),
                 "older_labels_replayed":len(base),
                 "frozen_classification_weights":True,
                 "training_rows_per_epoch":len(cached),
                 "history":history}

def run(seed_file:Path,baseline_file:Path,geometry_file:Path,
        correction_file:Path,blind_file:Path,out:Path)->dict:
    raw=seed_file.read_bytes()
    seed=json.loads(raw)
    validate_model(seed)
    original_report=json.loads(baseline_file.read_text())
    proof=json.loads(geometry_file.read_text())
    validate_proof(proof,raw,original_report)
    phases=validate_curriculum(json.loads(correction_file.read_text()))
    old_holdout=examples("holdout")
    # The previously used clinic blind is never trained on or selected against.
    old_exposed=phases["blind"]
    training=examples("train")+phases["correction"]
    checks=split_integrity(training,phases["development"],
                           new_blind_rows(json.loads(blind_file.read_text())),
                           old_holdout,old_exposed)
    improved,training_details=calibrate(
        seed,phases["correction"],phases["development"],old_holdout)
    if not frozen_classifier(seed,improved):
        raise ValueError("Operation classification was modified")
    old_before=measure(seed,old_holdout)
    old_after=measure(improved,old_holdout)
    assert old_before["operator_accuracy"]==old_after["operator_accuracy"]
    assert old_before["abstentions"]==old_after["abstentions"]
    # Fresh blind data is read and scored exactly once AFTER checkpoint choice.
    blind=new_blind_rows(json.loads(blind_file.read_text()))
    before=measure(seed,blind)
    after=measure(improved,blind)
    gain=round(before["conditional_strength_mae"]-
               after["conditional_strength_mae"],6)
    ok=(gain>=GATE["minimum_blind_strength_improvement"] and
        after["operator_accuracy"]>=GATE["minimum_blind_operator_accuracy"] and
        after["operator_accuracy"]>=before["operator_accuracy"] and
        after["abstentions"]<=before["abstentions"] and
        after["conditional_strength_mae"]<=GATE["maximum_blind_conditional_strength_mae"] and
        after["monotonic_strength_fraction"]>=GATE["minimum_blind_monotonic_fraction"] and
        old_after["conditional_strength_mae"]<=
        old_before["conditional_strength_mae"]+
        GATE["maximum_prior_strength_regression"])
    report={"schema":SCHEMA,
            "status":"validated_research_calibration" if ok
                     else "rejected_research_calibration",
            "seed_owned_checkpoint_sha256":checksum(raw),
            "verified_original_glb_proof_sha256":checksum(geometry_file.read_bytes()),
            "correction_source_sha256":checksum(correction_file.read_bytes()),
            "blind_source_sha256":checksum(blind_file.read_bytes()),
            "split_integrity":checks,"learning":training_details,
            "prior_before":old_before,"prior_after":old_after,
            "fresh_blind_before":before,"fresh_blind_after":after,
            "blind_strength_mae_improvement":gain,"gate":GATE,
            "class_head_frozen_identical":frozen_classifier(seed,improved),
            "blind_checked_once_after_dev_selection":True,
            "source_train_labels":"authored exact native geometry operator + strength targets",
            "uses_previous_rejected_clinic_student":False,
            "third_party_ai_generates_geometry":False,
            "android_deployable":False,
            "limitations":"Three original native operations, authored sentences, no external natural-language/general CAD benchmark or visual design superiority proven."}
    out.mkdir(parents=True,exist_ok=True)
    (out/"calibration_report.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"calibration_candidate.json").write_text(
        json.dumps(improved,separators=(",",":"))+"\n")
    (out/"validated_calibration.json").unlink(missing_ok=True)
    if ok:
        (out/"validated_calibration.json").write_text(
            json.dumps(improved,separators=(",",":"))+"\n")
    print(json.dumps({"status":report["status"],
                      "previous_accuracy":old_before["operator_accuracy"],
                      "new_blind_before":before,"new_blind_after":after,
                      "gain":gain,"frozen_classifier":report["class_head_frozen_identical"],
                      "selected_epoch":training_details["selected_epoch"]},indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("seed","baseline-evaluation","original-geometry-proof",
                 "correction-curriculum","fresh-blind","out"):
        p.add_argument("--"+flag,type=Path,required=True)
    a=p.parse_args()
    run(a.seed,a.baseline_evaluation,a.original_geometry_proof,
        a.correction_curriculum,a.fresh_blind,a.out)

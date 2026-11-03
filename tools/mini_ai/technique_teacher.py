#!/usr/bin/env python3
"""Teach Assetwright permitted procedural modeling operations directly.

Training targets are original, authored operation choices and causes, not
third-party model captions and not self-generated aesthetic approval.
A bounded bag-of-words learner retrieves operation IDs from design
critique language. It cannot execute arbitrary code or create new operations.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re

CURRICULUM="assetwright-vehicle-technique-curriculum-v1"
POLICY="assetwright-reviewed-technique-selection-policy-v1"
STATUS="assetwright-technique-training-report-v1"
CONTROLS={"canopySquareness","shoulderDefinition","fairedRepulsorMounts",
          "cockpitShoulderTransition","rearNacelleShrouding"}
METRICS={"roof_crown_width_ratio","mount_root_tip_taper_ratio",
         "body_cockpit_shoulder_span","engine_housing_flare_ratio"}
VARIANTS={"sculpted_canopy","integrated_aero","faired_mounts",
          "cockpit_bridge","rear_nacelle"}
ALIASES={
    "windscreen":"canopy","windshield":"canopy","glazing":"canopy",
    "glass":"canopy","greenhouse":"canopy","cockpit":"canopy",
    "roofline":"roof","oval":"dome","sphere":"bubble","spherical":"bubble",
    "overfenders":"shoulder","fenders":"shoulder","fender":"shoulder",
    "haunches":"shoulder","flanks":"shoulder","rocker":"shoulder",
    "wings":"shoulder","fairings":"fairing",
    "pipes":"rod","pipe":"rod","tubes":"rod","tube":"rod","tubing":"rod",
    "struts":"mount","strut":"mount","supports":"mount",
    "mounting":"mount","outrigger":"mount","outriggers":"mount",
    "hover":"repulsor","pods":"repulsor","pod":"repulsor",
    "cell":"repulsor","cells":"repulsor",
    "panels":"panel","slabs":"panel","slab":"panel",
}
STOP={"the","and","with","this","that","their","look","looks","make","more",
      "instead","from","into","rather","than","each","would","better",
      "should","need","needs","can","are","not","too","its","for","has",
      "these","them","use","using","give","add","some","there"}


def words(s:str)->list[str]:
    return [ALIASES.get(token,token) for token in re.findall(r"[a-z]+",s.lower())
            if len(token)>2 and token not in STOP]


def validate(raw:dict)->list[dict]:
    if not isinstance(raw,dict) or raw.get("schema")!=CURRICULUM:
        raise ValueError("Unknown original modeling technique curriculum")
    techniques=raw.get("techniques")
    if not isinstance(techniques,list) or not 1<=len(techniques)<=20:
        raise ValueError("Invalid technique roster")
    ids=set()
    controls=set()
    executable=0
    for item in techniques:
        if not isinstance(item,dict):
            raise ValueError("Malformed technique entry")
        key=item.get("id")
        if not isinstance(key,str) or not re.fullmatch("[a-z_]{5,72}",key) or key in ids:
            raise ValueError("Duplicate or invalid operation ID")
        ids.add(key)
        if not isinstance(item.get("why"),str) or len(item["why"])<20:
            raise ValueError("Every operation must explain why")
        if not isinstance(item.get("geometry_recipe"),list) or len(item["geometry_recipe"])<3:
            raise ValueError("No reproducible modeling sequence")
        if not isinstance(item.get("failure_modes"),list) or len(item["failure_modes"])<1:
            raise ValueError("No negative examples or constraints")
        state=item.get("execution_status")
        if state=="experimental_native_control":
            executable+=1
            control=item.get("control")
            if control not in CONTROLS or control in controls:
                raise ValueError("Unsupported/duplicate controlled operation")
            controls.add(control)
            value=item.get("value")
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1:
                raise ValueError("Unsafe operation parameter")
            if item.get("variant") not in VARIANTS:
                raise ValueError("Operation has no native benchmark variant")
            metric=item.get("target_measurement")
            if metric is not None and metric not in METRICS:
                raise ValueError("Unsupported visual proxy")
            samples=item.get("feedback_examples")
            heldout=item.get("holdout_feedback")
            if (not isinstance(samples,list) or len(samples)<8
                or not isinstance(heldout,list) or len(heldout)<3):
                raise ValueError("Not enough original labels to evaluate an operation")
            if not all(isinstance(t,str) and len(t)>=20 for t in samples+heldout):
                raise ValueError("Malformed training feedback")
        elif state=="requires_new_geometry_primitive":
            if any(item.get(k) is not None for k in ("control","value","variant","target_measurement")):
                raise ValueError("Unimplemented operation cannot falsely claim working controls")
            if item.get("feedback_examples") or item.get("holdout_feedback"):
                raise ValueError("Unimplemented operation cannot supervise existing planner")
        else:
            raise ValueError("Unknown technique status")
    if executable<2:
        raise ValueError("Not enough executable modeling techniques")
    return techniques


def _fit(executable:list[dict])->dict:
    # Multinomial Naive Bayes with explicit count smoothing, fully offline.
    classes=[t["id"] for t in executable]
    vocabulary=set()
    counts={}
    for t in executable:
        tokens=[x for phrase in t["feedback_examples"] for x in words(phrase)]
        vocabulary.update(tokens)
        counts[t["id"]]=Counter(tokens)
    vocab=sorted(vocabulary)
    n_tokens={key:sum(counter.values()) for key,counter in counts.items()}
    weights={}
    for key,counter in counts.items():
        denominator=n_tokens[key]+len(vocab)
        weights[key]={word:round(math.log((counter[word]+1)/denominator),9)
                      for word in vocab}
    return {"schema":POLICY,"classes":classes,"vocabulary":vocab,"log_likelihood":weights,
            "min_confidence_gap":0.35,"source":"Forge-authored original technique critique labels",
            "trained_on_private_user_assets":False,"auto_execute":False,
            "generation_code_modified":False}


def predict(policy:dict,description:str)->tuple[str|None,float]:
    tokens=[t for t in words(description) if t in policy["vocabulary"]]
    if not tokens:
        return None,0.
    vocab_scores={}
    for name in policy["classes"]:
        row=policy["log_likelihood"][name]
        vocab_scores[name]=sum(row[t] for t in tokens)/math.sqrt(len(tokens))
    scores=sorted(vocab_scores.items(),key=lambda x:(-x[1],x[0]))
    gap=scores[0][1]-(scores[1][1] if len(scores)>1 else scores[0][1]-1)
    return (scores[0][0] if gap>=policy["min_confidence_gap"] else None,
            round(gap,5))


def train(raw:dict)->tuple[dict,dict|None]:
    techniques=validate(raw)
    active=[t for t in techniques if t["execution_status"]=="experimental_native_control"]
    policy=_fit(active)
    cases=[]
    matrix={t["id"]:{"correct":0,"total":0} for t in active}
    for t in active:
        for text in t["holdout_feedback"]:
            predicted,gap=predict(policy,text)
            right=predicted==t["id"]
            cases.append({"expected":t["id"],"predicted":predicted,"correct":right,
                          "confidence_gap":gap,"phrase":text})
            matrix[t["id"]]["total"]+=1
            matrix[t["id"]]["correct"]+=int(right)
    accuracy=sum(x["correct"] for x in cases)/len(cases)
    baseline=max(x["total"] for x in matrix.values())/len(cases)
    accepted=accuracy>=.75 and accuracy>baseline+.15
    report={
        "schema":STATUS,"status":"technique_selector_validated" if accepted
            else "selector_rejected_holdout",
        "active_operations":len(active),"planned_unimplemented_operations":
            len(techniques)-len(active),
        "original_training_feedback":sum(len(x["feedback_examples"]) for x in active),
        "heldout_feedback":len(cases),"heldout_accuracy":round(accuracy,5),
        "majority_baseline_accuracy":round(baseline,5),
        "per_operation":matrix,"holdout_cases":cases,
        "trained_on_unverified_generated_meshes":False,
        "allowed_to_modify_android_geometry":False,
        "note":"Supervised technique name retrieval from authored feedback, not 3D topology learning."
    }
    return report,policy if accepted else None


def run(source:Path,out:Path)->dict:
    report,model=train(json.loads(source.read_text(encoding="utf-8")))
    out.mkdir(parents=True,exist_ok=True)
    (out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    if model is None:
        # An earlier run's accepted model must never survive failed
        # validation in a reused output directory.
        (out/"validated_selector.json").unlink(missing_ok=True)
    if model is not None:
        (out/"validated_selector.json").write_text(
            json.dumps(model,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="holdout_cases"},indent=2))
    return report


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--curriculum",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    args=cli.parse_args()
    run(args.curriculum,args.out)

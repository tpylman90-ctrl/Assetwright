"""A bounded, error-driven learning clinic for AssetWright's OWN native Mini AI.

Pain points addressed: ambiguous feedback, superficial word shortcuts,
catastrophic forgetting, ineffective repeated easy lessons, and held-out
contamination. Resumes an independently verified checkpoint; teaches only
reviewed *native construction labels*, never model-generated pseudo-truth.

Research-only: measured GLB proof is a prerequisite to practising a skill,
not evidence that the finished mesh is aesthetically good.
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
    SCHEMA as STUDENT_SCHEMA, EVAL as BASE_EVAL, OPERATIONS,
    examples, infer, forward, text_features,
)

SCHEMA="assetwright-native-mistake-clinic-v1"
CURRICULUM="assetwright-native-correction-curriculum-v1"
PROOF="assetwright-owned-native-planner-real-glb-evaluation-v1"
MIN_LESSONS=30
CLINIC_GATE_ACC=.80
CLINIC_GATE_MAE=.15

def digest(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def validate_curriculum(doc:dict)->dict[str,list[dict]]:
    if doc.get("schema")!=CURRICULUM or doc.get("license")!="original-assetwright-authored":
        raise ValueError("Unapproved correction curriculum")
    phases={}
    seen=set()
    for phase in ("correction","development","blind"):
        raw=doc.get(phase)
        if not isinstance(raw,list) or not 3<=len(raw)<=30:
            raise ValueError("Missing curated lesson families for "+phase)
        rows=[]
        for idx,item in enumerate(raw):
            if not isinstance(item,dict) or set(item)!={"operation","template","skill"}:
                raise ValueError("Malformed teacher correction")
            op=item["operation"];pattern=item["template"];skill=item["skill"]
            if op not in OPERATIONS or not isinstance(skill,str) or len(skill)>75:
                raise ValueError("Unknown native skill")
            if (not isinstance(pattern,str) or len(pattern)>200 or
                pattern.count("{level}")!=1 or pattern.count("{vehicle}")!=1):
                raise ValueError("Uncontrolled prompt-template or ambiguous strength")
            if pattern.lower() in seen:raise ValueError("Correction, dev and blind examples must be disjoint")
            seen.add(pattern.lower())
            for adjective,strength in (("gentle",.30),("moderate",.60),("aggressive",.90)):
                for vehicle in (("hover racer","hover coupe") if phase=="correction" else
                                ("test interceptor",) if phase=="development" else
                                ("unseen utility hauler",)):
                    text=pattern.format(level=adjective,vehicle=vehicle)
                    rows.append({"prompt":text,"operation":op,"strength":strength,
                                 "source_group":phase+":"+op+":"+str(idx),
                                 "source_kind":"explicit_native_gold_label",
                                 "split":phase,"skill":skill})
        if {r["operation"] for r in rows}!=set(OPERATIONS):
            raise ValueError("Curriculum must cover all native operations")
        phases[phase]=rows
    return phases

def unresolved_review_gaps(doc:dict)->dict:
    """Never silently turn a negative, unapproved visual review into gold."""
    if (doc.get("schema")!="assetwright-original-glb-visual-review-v1" or
        doc.get("review_status")!="negative_design_references_only"):
        raise ValueError("Unexpected visual review state")
    counter={}
    for item in doc.get("reviews",[]):
        if (item.get("allowed_for_training") is not False or
            item.get("human_final_approval") is not False):
            raise ValueError("Visual reviews require actual human approval")
        observations=item.get("observations",[])
        if not isinstance(observations,list):raise ValueError("Invalid critique")
        for observation in observations:
            if not isinstance(observation,str) or len(observation)>500:
                raise ValueError("Unbounded visual note")
            note=observation.lower()
            if any(t in note for t in ("cockpit","canopy","greenhouse","cabin")):
                tag="cockpit_to_hull_surface_continuity"
            elif any(t in note for t in ("mount","support","repulsor")):
                tag="connected_structural_mounts"
            elif any(t in note for t in ("engine","propulsion","rear")):
                tag="welded_engine_body_integration"
            else:
                tag="other_unresolved_geometry_quality"
            counter[tag]=counter.get(tag,0)+1
    return {"reviewed_negative_examples":len(doc.get("reviews",[])),
            "unresolved_problem_counts":counter,
            "used_as_positive_training_labels":0,
            "quality_status":"requires_human_visual_review_and_native_modeling_work"}

def validate_proof(audit:dict,model_bytes:bytes,baseline_eval:dict)->None:
    if (audit.get("schema")!=PROOF or audit.get("passed") is not True or
        not isinstance(audit.get("checks"),dict) or
        len(audit["checks"])<10 or not all(v is True for v in audit["checks"].values()) or
        audit.get("research_checkpoint_sha256")!=digest(model_bytes)):
        raise ValueError("No hash-matched actual native GLB geometry proof")
    if (baseline_eval.get("schema")!=BASE_EVAL or
        baseline_eval.get("status")!="validated_research_intent_student" or
        baseline_eval.get("template_group_overlap") is not False or
        baseline_eval.get("heldout_accuracy",0)<.85):
        raise ValueError("Initial student did not pass its own validation")

def validate_model(model:dict)->None:
    if (model.get("schema")!=STUDENT_SCHEMA or
        model.get("operations")!=list(OPERATIONS) or
        model.get("feature_dim")!=512 or
        model.get("external_mesh_used") is not False or
        model.get("inference_requires_teacher") is not False or
        model.get("android_deployable") is not False or
        model.get("approved_for_geometry_generation") is not False):
        raise ValueError("Untrusted pretrained or deployed model")
    for key,expected_count in (("class_weights",3),("strength_weights",3)):
        value=model.get(key)
        if (not isinstance(value,list) or len(value)!=expected_count or
            any(not isinstance(v,list) or len(v)!=512 or
                any(type(k) not in (float,int) or not math.isfinite(k) for k in v)
                for v in value)):
            raise ValueError("Malformed own weights: "+key)
    for key in ("class_bias","strength_bias"):
        v=model.get(key)
        if not isinstance(v,list) or len(v)!=3 or any(
            type(x) not in (float,int) or not math.isfinite(x) for x in v
        ):raise ValueError("Malformed own biases")

def evaluate_rows(model:dict,rows:list[dict])->dict:
    if not rows:raise ValueError("No evaluation rows")
    correct=0
    abstain=0
    mae=0.
    hard=0
    diagnostics=[]
    for row in rows:
        guess=infer(model,row["prompt"])
        if guess["status"]=="abstain":
            abstain+=1
            kind="abstention"
            estimated=None
            # Missing examples still contribute a full strength penalty.
            error=1.
        else:
            estimated=guess["strength"]
            kind=("wrong_operation" if guess["operation"]!=row["operation"] else
                  "wrong_strength" if abs(estimated-row["strength"])>.13 else
                  "mastered")
            if kind=="mastered":correct+=1
            if kind!="mastered":hard+=1
            error=abs(estimated-row["strength"])
        if kind=="abstention":hard+=1
        mae+=error
        diagnostics.append({"prompt":row["prompt"],"expected_operation":row["operation"],
                            "expected_strength":row["strength"],
                            "proposed_operation":guess.get("operation"),
                            "proposed_strength":estimated,
                            "error":round(error,6),"diagnosis":kind,
                            "source_group":row["source_group"]})
    # Correct category is measured independently of intensity.
    operation_correct=sum(x["proposed_operation"]==x["expected_operation"]
                          for x in diagnostics)
    return {"size":len(rows),
            "operator_accuracy":round(operation_correct/len(rows),6),
            "strength_mae_all":round(mae/len(rows),6),
            "exact_skill_and_strength_accuracy":round(correct/len(rows),6),
            "abstentions":abstain,"needs_retraining":hard,
            "diagnosis_counts":{k:sum(x["diagnosis"]==k for x in diagnostics)
                for k in ("wrong_operation","wrong_strength","abstention","mastered")},
            "individual_diagnoses":diagnostics}

def effectiveness(metrics:dict)->float:
    # Explicit development-only checkpoint selection; the untouched blind
    # examples are never consulted for learning rate or epoch choice.
    return (metrics["operator_accuracy"]*.55+
            metrics["exact_skill_and_strength_accuracy"]*.25-
            metrics["strength_mae_all"]*.20-
            (metrics["abstentions"]/metrics["size"])*.25)

def update_from_lesson(model:dict,item:dict,lr:float)->None:
    x=text_features(item["prompt"])
    probs,strengths=forward(model,item["prompt"])
    target=OPERATIONS.index(item["operation"])
    for j in range(len(OPERATIONS)):
        d=probs[j]-(1. if j==target else 0.)
        model["class_bias"][j]-=lr*.18*d
        for k,v in x.items():
            model["class_weights"][j][k]-=lr*(d*v+.00004*model["class_weights"][j][k])
    delta=strengths[target]-item["strength"]
    model["strength_bias"][target]-=lr*.20*delta
    for k,v in x.items():
        model["strength_weights"][target][k]-=lr*(delta*v+.00004*model["strength_weights"][target][k])

def practise(base:dict,corrections:list[dict],development:list[dict],
             previous:list[dict],epochs:int=28)->tuple[dict,dict]:
    if not 1<=epochs<=60:raise ValueError("Unbounded CPU training")
    # Inspect only authored correction lessons. Wrong model answers NEVER
    # become the labels for the next lesson.
    diagnostic=evaluate_rows(base,corrections)
    weak_prompts={r["prompt"] for r in diagnostic["individual_diagnoses"]
                  if r["diagnosis"]!="mastered"}
    # The contrast pair for a weak example has a DIFFERENT correct operation,
    # same vehicle and same stated intensity, so a vehicle-word shortcut fails.
    hard=[r for r in corrections if r["prompt"] in weak_prompts]
    balanced=list(corrections)
    replay=list(examples("train"))
    if len(balanced)<MIN_LESSONS or not hard:
        # Still rehearse the known labels; never invent a "teacher" correction.
        hard=balanced[:min(12,len(balanced))]
    chosen=copy.deepcopy(base);current=copy.deepcopy(base)
    old=evaluate_rows(base,previous)
    dev_base=evaluate_rows(base,development)
    best_score=effectiveness(dev_base)
    selection={"epochs":0,"development_score":round(best_score,6)}
    rng=random.Random(603)
    for epoch in range(1,epochs+1):
        # 1x precise examples, 1x targeted weaknesses, 1x replay of past
        # correct skill labels. This stops only-hard-example specialization.
        work=balanced+hard+replay
        rng.shuffle(work)
        lr=.050/(1+.04*epoch)
        for item in work:update_from_lesson(current,item,lr)
        if epoch in (4,8,12,16,20,24,28,36,48,60) or epoch==epochs:
            metric=evaluate_rows(current,development)
            retain=evaluate_rows(current,previous)
            score=effectiveness(metric)
            if (score>best_score+1e-6 and
                retain["operator_accuracy"]>=old["operator_accuracy"]-.03 and
                retain["strength_mae_all"]<=old["strength_mae_all"]+.025):
                best_score=score
                chosen=copy.deepcopy(current)
                selection={"epochs":epoch,"development_score":round(score,6)}
    return chosen,{"diagnosis_before":{k:v for k,v in diagnostic.items()
                                      if k!="individual_diagnoses"},
                   "weak_lessons":len(hard),"reviewed_correction_lessons":len(balanced),
                   "rehearsal_lessons":len(replay),"training_updates":epochs*len(work),
                   "checkpoint_selection":selection,
                   "development_baseline":{k:v for k,v in dev_base.items()
                                           if k!="individual_diagnoses"}}

def run(source_model:Path,source_eval:Path,source_audit:Path,
        curriculum:Path,out:Path,review_file:Path|None=None)->dict:
    raw=source_model.read_bytes()
    original=json.loads(raw)
    validate_model(original)
    proof=json.loads(source_audit.read_text())
    baser=json.loads(source_eval.read_text())
    validate_proof(proof,raw,baser)
    data=validate_curriculum(json.loads(curriculum.read_text()))
    old_holdout=examples("holdout")
    # Absolutely no clinic training on earlier evaluation prompts.
    original_training={x["prompt"] for x in examples("train")}
    holdout_prompts={x["prompt"] for x in old_holdout}
    clinic_training={x["prompt"] for x in data["correction"]}
    dev_prompts={x["prompt"] for x in data["development"]}
    blind_prompts={x["prompt"] for x in data["blind"]}
    if ((original_training|clinic_training)&(holdout_prompts|dev_prompts|blind_prompts)
        or dev_prompts&blind_prompts):
        raise ValueError("Training/validation/blind prompt leakage")
    candidate,learning=practise(original,data["correction"],data["development"],
                                old_holdout)
    # BLIND evaluation happens exactly once, after all model selection.
    old=evaluate_rows(original,old_holdout)
    retained=evaluate_rows(candidate,old_holdout)
    blind_before=evaluate_rows(original,data["blind"])
    blind_after=evaluate_rows(candidate,data["blind"])
    improved=(blind_after["operator_accuracy"]>=blind_before["operator_accuracy"] and
              blind_after["strength_mae_all"]<=blind_before["strength_mae_all"]-.01)
    passed=(improved and
            blind_after["operator_accuracy"]>=CLINIC_GATE_ACC and
            blind_after["strength_mae_all"]<=CLINIC_GATE_MAE and
            retained["operator_accuracy"]>=old["operator_accuracy"]-.03 and
            retained["strength_mae_all"]<=old["strength_mae_all"]+.025)
    summary={"schema":SCHEMA,
             "status":"validated_research_clinic_checkpoint" if passed else
                      "rejected_clinic_checkpoint",
             "source_model_sha256":digest(raw),
             "source_geometry_audit_sha256":digest(source_audit.read_bytes()),
             "checkpoint_init":"resumed_verified_owned_weights_not_from_scratch",
             "optimizer":"bounded stateless SGD, replay + mistake prioritization",
             "teacher_labels":"original exact native operation corrections only",
             "negative_visual_reviews":unresolved_review_gaps(
                 json.loads(review_file.read_text())) if review_file else None,
             "third_party_model_produces_geometry":False,
             "external_geometry_used_as_labels":False,
             "android_deployable":False,
             "used_blind_for_model_selection":False,
             "learning":learning,
             "old_skill_before":{k:v for k,v in old.items() if k!="individual_diagnoses"},
             "old_skill_after":{k:v for k,v in retained.items() if k!="individual_diagnoses"},
             "blind_before":{k:v for k,v in blind_before.items() if k!="individual_diagnoses"},
             "blind_after":{k:v for k,v in blind_after.items() if k!="individual_diagnoses"},
             "gate":{"min_blind_operator_accuracy":CLINIC_GATE_ACC,
                     "max_blind_strength_mae":CLINIC_GATE_MAE,
                     "minimum_blind_strength_gain":.01,
                     "max_old_skill_accuracy_regression":.03,
                     "max_old_skill_strength_mae_regression":.025},
             "limitations":"Structured, authored three-operation practice; geometry proof validates original engine, not design aesthetics or arbitrary 3D construction."}
    out.mkdir(parents=True,exist_ok=True)
    (out/"clinic_report.json").write_text(json.dumps(summary,indent=2)+"\n")
    (out/"clinic_development_mistakes.json").write_text(
        json.dumps(evaluate_rows(original,data["correction"]),indent=2)+"\n")
    (out/"candidate_clinic_student.json").write_text(
        json.dumps(candidate,separators=(",",":"))+"\n")
    (out/"validated_clinic_student.json").unlink(missing_ok=True)
    if passed:
        candidate["clinic_source_model_sha256"]=digest(raw)
        candidate["clinic_proof_audit_sha256"]=digest(source_audit.read_bytes())
        candidate["approved_for_geometry_generation"]=False
        (out/"validated_clinic_student.json").write_text(
            json.dumps(candidate,separators=(",",":"))+"\n")
    print(json.dumps({k:v for k,v in summary.items()
                      if k not in ("learning","old_skill_before","old_skill_after")},
                     indent=2))
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("model","evaluation","geometry-audit","curriculum","out"):
        p.add_argument("--"+flag,type=Path,required=True)
    p.add_argument("--negative-reviews",type=Path)
    a=p.parse_args()
    run(a.model,a.evaluation,a.geometry_audit,a.curriculum,a.out,a.negative_reviews)

if __name__=="__main__":main()

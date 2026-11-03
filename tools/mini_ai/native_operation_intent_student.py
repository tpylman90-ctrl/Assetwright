"""Train our own CPU-only text -> verified NATIVE construction-operation student.

The owned model learns from deliberately authored descriptions paired with
our three executable MiniGeometry controls, not from teacher-generated meshes.
Zero-to-CAD and DINOv2 serve separate CAD/visual research gates; their
pretrained outputs cannot be substituted for native generated geometry.

Research limitation: small authored vocabulary; no arbitrary text-to-CAD or
full geometry-program synthesis. Hold out instruction TEMPLATES, not samples.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re

SCHEMA="assetwright-owned-native-operation-intent-student-v1"
EVAL="assetwright-native-operator-intent-evaluation-v1"
OPERATIONS=("recess_rear_socket","sculpt_cockpit_shoulder","loft_rear_nacelle")
DIM=512
LEVELS={"subtle":.30,"moderate":.60,"strong":.90}
VEHICLES_TRAIN=("hover racer","hover coupe","hover SUV")
VEHICLES_HOLDOUT=("interceptor hovercraft","experimental speedster")
# Every instruction/label is an ORIGINAL supervised native operation lesson;
# CAD corpus rows and DINOv2 embeddings are NOT falsely labeled as prompts.
TEMPLATES={
    OPERATIONS[0]:{
        "train":(
            "Cut a {level} circular rear engine socket into the {vehicle}",
            "Give the {vehicle} a {level} blind cavity behind its drive",
            "Sink its engine into a {level} round recess on the {vehicle}",
            "Add a {level} rear propulsion opening inside the {vehicle} hull",
            "Carve a {level} circular socket in the {vehicle} tail"
        ),
        "holdout":(
            "The {vehicle} needs a {level} rear drive recess carved into its hull",
            "Make a {level} circular indentation for the engine of this {vehicle}"
        )
    },
    OPERATIONS[1]:{
        "train":(
            "Sculpt a {level} cockpit shoulder transition on the {vehicle}",
            "Make the {vehicle} cabin-to-hull transition {level} and flowing",
            "Add a {level} integrated fender shoulder around this {vehicle} canopy",
            "Give the {vehicle} a {level} flowing upper-hull cockpit bridge",
            "Widen the {vehicle} cockpit-side shoulder with a {level} loft"
        ),
        "holdout":(
            "The {vehicle} needs a {level} sculpted shoulder joining its canopy to the hull",
            "Build a {level} smoothly lofted cockpit body transition on the {vehicle}"
        )
    },
    OPERATIONS[2]:{
        "train":(
            "Loft a {level} faired housing around the {vehicle} rear nacelle",
            "Make the {vehicle} engine casing use a {level} tapered profile",
            "Create a {level} swept rear thruster shroud for the {vehicle}",
            "Give the {vehicle} a {level} profiled drive housing loft",
            "Add a {level} contoured propulsion nacelle shroud to this {vehicle}"
        ),
        "holdout":(
            "The {vehicle} needs a {level} tapered engine housing in the back",
            "Form a {level} swept nacelle fairing around the {vehicle} propulsion unit"
        )
    }
}

def text_features(prompt:str)->dict[int,float]:
    if not isinstance(prompt,str) or len(prompt)>500 or not prompt.strip():
        raise ValueError("Invalid native design instruction")
    words=re.findall(r"[a-z0-9]+",prompt.lower())
    # Word and sequential-word features; native student does not need a teacher.
    tokens={"u:"+w for w in words}
    tokens.update("b:"+a+"_"+b for a,b in zip(words,words[1:]))
    if not tokens: raise ValueError("No input terms")
    x={}
    scale=1/math.sqrt(len(tokens))
    for t in sorted(tokens):
        k=int(hashlib.blake2s(t.encode(),digest_size=4).hexdigest(),16)%DIM
        x[k]=x.get(k,0.)+scale
    return x

def examples(split:str)->list[dict]:
    if split not in ("train","holdout"):raise ValueError("Invalid curriculum partition")
    vehicles=VEHICLES_TRAIN if split=="train" else VEHICLES_HOLDOUT
    rows=[]
    for operation,parts in TEMPLATES.items():
        for template_i,template in enumerate(parts[split]):
            for level,strength in LEVELS.items():
                for vehicle in vehicles:
                    prompt=template.format(level=level,vehicle=vehicle)
                    rows.append({"prompt":prompt,"operation":operation,
                                 "strength":strength,
                                 "source_group":f"{operation}:{split}:template_{template_i}",
                                 "source_kind":"authored_native_operation_recipe",
                                 "split":split})
    return rows

def init(seed:int=41)->dict:
    rng=random.Random(seed)
    return {"schema":SCHEMA,"operations":list(OPERATIONS),"feature_dim":DIM,
            "class_weights":[[rng.uniform(-.003,.003) for _ in range(DIM)] for _ in OPERATIONS],
            "class_bias":[0.]*len(OPERATIONS),
            "strength_weights":[[0.]*DIM for _ in OPERATIONS],
            "strength_bias":[.6]*len(OPERATIONS),
            "inference_requires_teacher":False,"external_mesh_used":False,
            "android_deployable":False}

def softmax(values:list[float])->list[float]:
    high=max(values)
    exp=[math.exp(v-high) for v in values]
    return [v/sum(exp) for v in exp]

def forward(model:dict,prompt:str)->tuple[list[float],list[float]]:
    x=text_features(prompt)
    probs=softmax([b+sum(row[i]*v for i,v in x.items())
                  for row,b in zip(model["class_weights"],model["class_bias"])])
    strengths=[b+sum(row[i]*v for i,v in x.items())
               for row,b in zip(model["strength_weights"],model["strength_bias"])]
    return probs,[max(0.,min(1.,v)) for v in strengths]

def train(rows:list[dict],epochs:int=125)->dict:
    if len(rows)<60 or {r["operation"] for r in rows}!=set(OPERATIONS):
        raise ValueError("Insufficient supervised construction examples")
    model=init();rng=random.Random(2026);samples=rows[:]
    for epoch in range(epochs):
        rng.shuffle(samples)
        rate=.15/(1+.016*epoch)
        for record in samples:
            x=text_features(record["prompt"])
            probs,strengths=forward(model,record["prompt"])
            target=OPERATIONS.index(record["operation"])
            for j in range(len(OPERATIONS)):
                err=probs[j]-(1. if j==target else 0.)
                model["class_bias"][j]-=rate*.18*err
                for k,v in x.items():
                    model["class_weights"][j][k]-=rate*(err*v+.00004*model["class_weights"][j][k])
            # Strength supervision belongs to the TRUE labeled construction
            # operator. Don't invent labels for operations not in the example.
            delta=strengths[target]-record["strength"]
            model["strength_bias"][target]-=rate*.20*delta
            for k,v in x.items():
                model["strength_weights"][target][k]-=rate*(delta*v+.00004*model["strength_weights"][target][k])
    model.update(training_lessons=len(rows),epochs=epochs,
                 label_origin="authored exact native operation controls",
                 approved_for_geometry_generation=False)
    return model

def infer(model:dict,prompt:str,*,allow_low_confidence:bool=False)->dict:
    if (model.get("schema")!=SCHEMA or model.get("external_mesh_used") is not False or
        model.get("inference_requires_teacher") is not False or
        model.get("operations")!=list(OPERATIONS)):
        raise ValueError("Untrusted native operation student")
    probs,values=forward(model,prompt)
    ordered=sorted(range(len(probs)),key=lambda i:probs[i],reverse=True)
    chosen=ordered[0]
    if not allow_low_confidence and (probs[chosen]<.55 or probs[chosen]-probs[ordered[1]]<.15):
        return {"status":"abstain","reason":"Insufficient native operator intent confidence",
                "confidence":round(probs[chosen],6)}
    return {"status":"native_research_operation_proposal",
            "operation":OPERATIONS[chosen],"strength":round(values[chosen],5),
            "confidence":round(probs[chosen],6),
            "teacher_required_at_inference":False,"external_mesh_used":False,
            "android_deployable":False}

def evaluate(model:dict,heldout:list[dict])->dict:
    correct=0;mae=0.;abstain=0;confusion={}
    for row in heldout:
        proposal=infer(model,row["prompt"])
        if proposal["status"]=="abstain":abstain+=1;continue
        pred=proposal["operation"]
        confusion[pred]=confusion.get(pred,0)+1
        correct+=pred==row["operation"]
        mae+=abs(proposal["strength"]-row["strength"])
    accepted=max(1,len(heldout)-abstain)
    # Balanced 3-class baseline is 1/3; for intensities the constant
    # .60 baseline MAE is exactly .20 across .30/.60/.90.
    accuracy=correct/len(heldout)
    strength_mae=mae/accepted
    passed=(accuracy>=.85 and abstain<=len(heldout)*.10 and
            strength_mae<.105 and strength_mae<.2*.75)
    return {"schema":EVAL,"status":"validated_research_intent_student" if passed else "student_rejected_heldout",
            "training_examples":len(examples("train")),
            "heldout_examples":len(heldout),
            "heldout_template_groups":len({r["source_group"] for r in heldout}),
            "template_group_overlap":bool({r["source_group"] for r in examples("train")} &
                                          {r["source_group"] for r in heldout}),
            "heldout_accuracy":round(accuracy,6),"heldout_abstentions":abstain,
            "heldout_strength_mae":round(strength_mae,6),
            "baseline_operator_accuracy":round(1/3,6),
            "baseline_strength_mae":.2,
            "coverage":"Three existing bounded original geometry operations; authored prompts",
            "zero_to_cad_operations_are_not_text_labels":True,
            "dinov2_features_not_falsely_used_as_prompt_labels":True,
            "trained_model_creates_no_mesh":True,"android_auto_promotion":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--epochs",type=int,default=125)
    a=p.parse_args()
    if not 1<=a.epochs<=300: raise SystemExit("Invalid bounded training epochs")
    model=train(examples("train"),epochs=a.epochs)
    report=evaluate(model,examples("holdout"))
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (a.out/"candidate_intent_student.json").write_text(json.dumps(model,separators=(",",":"))+"\n")
    (a.out/"validated_intent_student.json").unlink(missing_ok=True)
    if report["status"]=="validated_research_intent_student":
        (a.out/"validated_intent_student.json").write_text(json.dumps(model,separators=(",",":"))+"\n")
    print(json.dumps(report,indent=2))
    if report["status"]!="validated_research_intent_student":raise SystemExit(2)

if __name__=="__main__":main()

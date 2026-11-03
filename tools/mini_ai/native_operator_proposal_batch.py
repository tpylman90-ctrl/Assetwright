"""Use independently held-out OWNED student to request three REAL native GLBs.

This strictly reads validated research checkpoints; it does not import any
outside AI geometry. Any operation/strength selection comes from trained
AssetWright weights, rather than a hardcoded operation switch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from native_operation_intent_student import infer,SCHEMA,EVAL,OPERATIONS

REQUEST="assetwright-owned-native-planner-batch-v1"
PROOF_PROMPTS=[
    "The interceptor hovercraft needs a strong rear drive recess carved into its hull",
    "The interceptor hovercraft needs a strong sculpted shoulder joining its canopy to the hull",
    "The interceptor hovercraft needs a strong tapered engine housing in the back",
]

def batch(model:dict,report:dict,source_sha:str)->dict:
    if (model.get("schema")!=SCHEMA or
        model.get("external_mesh_used") is not False or
        model.get("approved_for_geometry_generation") is not False or
        model.get("inference_requires_teacher") is not False or
        report.get("schema")!=EVAL or
        report.get("status")!="validated_research_intent_student" or
        report.get("template_group_overlap") is not False or
        report.get("heldout_accuracy",0)<.85 or
        report.get("heldout_strength_mae",1)>.105):
        raise ValueError("Unverified original native planner checkpoint")
    if len(source_sha)!=64:
        raise ValueError("Model SHA missing")
    proposals=[]
    for prompt in PROOF_PROMPTS:
        result=infer(model,prompt)
        if result["status"]!="native_research_operation_proposal":
            raise ValueError("Native student abstained; no manual fallback")
        if result["strength"]<.45:
            raise ValueError("Native student strength inadequate for controlled geometry test")
        proposals.append({"prompt":prompt,**result})
    if {p["operation"] for p in proposals}!=set(OPERATIONS):
        raise ValueError("Native learner did not independently select all three operations")
    return {"schema":REQUEST,"model_sha256":source_sha,
            "source":"Owned student weights trained on authored native geometry lessons",
            "zero_to_cad_teacher":"Prior separately verified CAD operation-sequence study",
            "dinov2_teacher":"Prior separately verified visual feature distillation study",
            "teacher_model_used_to_generate_geometry":False,
            "external_mesh_used":False,"android_deployable":False,
            "source_validation":report,"proposals":proposals}

def run(weights:Path,evaluation:Path,out:Path)->dict:
    raw=weights.read_bytes()
    proof=batch(json.loads(raw),json.loads(evaluation.read_text()),
                hashlib.sha256(raw).hexdigest())
    out.mkdir(parents=True,exist_ok=True)
    (out/"native_planner_proposals.json").write_text(json.dumps(proof,indent=2)+"\n")
    lines=[
        "schema="+REQUEST,
        "external_mesh_used=false",
        "count=3",
        "model_sha256="+proof["model_sha256"]
    ]
    for index,proposal in enumerate(proof["proposals"]):
        lines += [f"proposal{index}.operation="+proposal["operation"],
                  f"proposal{index}.strength="+str(proposal["strength"])]
    (out/"operation_batch.properties").write_text("\n".join(lines)+"\n")
    print(json.dumps({"status":"verified_owned_inference_batch",
                      "predictions":[{"operation":p["operation"],
                                      "strength":p["strength"],
                                      "confidence":p["confidence"]}
                                     for p in proof["proposals"]]},indent=2))
    return proof

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--evaluation",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.model,a.evaluation,a.out)

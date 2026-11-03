#!/usr/bin/env python3
"""Causal technique exercises from genuine generated GLB benchmark contrasts.

These are interventions with a known changed control and verified SHA-linked
geometry, NOT visually approved model improvements or self-generated labels.
An effect is 'demonstrated' only for a measured, structural-safe change.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

from technique_teacher import validate

SCHEMA="assetwright-technique-effect-audit-v1"

def evaluate(curriculum:dict,benchmark:dict)->dict:
    techniques=validate(curriculum)
    if benchmark.get("schema")!="assetwright-generator-quality-loop-v1":
        raise ValueError("Unknown real GLB geometry benchmark")
    cases=benchmark.get("candidates")
    if not isinstance(cases,list) or not cases:
        raise ValueError("No original generated GLB candidates")
    by_case={}
    for row in cases:
        if not isinstance(row,dict):
            raise ValueError("Invalid original GLB candidate")
        key=(row.get("case"),row.get("variant"))
        if key in by_case:
            raise ValueError("Duplicate candidate contradicts causal comparison")
        sha=row.get("source_sha256")
        if not isinstance(sha,str) or len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("Missing original GLB checksum")
        by_case[key]=row
    names=sorted({key[0] for key in by_case})
    results=[]
    for item in techniques:
        result={
            "technique_id":item["id"],"modeling_operation":item["modeling_operation"],
            "execution_status":item["execution_status"],
            "control":item["control"],"value":item["value"],
            "purpose":item["purpose"],"why":item["why"],
            "instructions":item["geometry_recipe"],
            "failure_modes":item["failure_modes"],"target_metric":item["target_measurement"],
            "approved_as_visual_training":False,
            "source":"Original Assetwright generator control intervention"
        }
        if item["execution_status"]!="experimental_native_control":
            result["outcome"]="unimplemented_operation"
            result["contrasts"]=[]
            results.append(result)
            continue
        if item["target_measurement"] is None:
            result["outcome"]="requires_objective_measurement"
            result["contrasts"]=[]
            results.append(result)
            continue
        pairs=[]
        for name in names:
            before=by_case.get((name,"baseline"))
            after=by_case.get((name,item["variant"]))
            if before is None or after is None:
                continue
            a=before.get("design_proxy_metrics",{}).get(item["target_measurement"])
            b=after.get("design_proxy_metrics",{}).get(item["target_measurement"])
            valid=all([
                before.get("passed") is True,after.get("passed") is True,
                type(a) in (int,float),type(b) in (int,float),
                math.isfinite(a) if type(a) in (int,float) else False,
                math.isfinite(b) if type(b) in (int,float) else False,
            ])
            delta=round(b-a,5) if valid else None
            matched=bool(valid and delta >= item["min_increase"])
            pairs.append({
                "case":name,
                "before_sha256":before["source_sha256"],
                "after_sha256":after["source_sha256"],
                "before_measurement":a,"after_measurement":b,
                "delta":delta,"passed_structural_checks":valid,
                "effect_demonstrated":matched,
                "source_reconstruction_not_training":True
            })
        success=sum(x["effect_demonstrated"] for x in pairs)
        result.update(
            cases_tested=len(pairs),positive_effects=success,contrasts=pairs,
            outcome="measured_operation_effect" if len(pairs)>=3 and
                success>=math.ceil(len(pairs)*.75) else "effect_not_demonstrated"
        )
        results.append(result)
    demonstrated=sum(x["outcome"]=="measured_operation_effect" for x in results)
    return {
        "schema":SCHEMA,
        "source":"Exact SHA-verified original generated GLB variants",
        "number_of_techniques":len(results),
        "techniques_with_measured_effect":demonstrated,
        "techniques_requiring_new_geometry":sum(x["outcome"]=="unimplemented_operation" for x in results),
        "techniques_without_independent_measurement":sum(x["outcome"]=="requires_objective_measurement" for x in results),
        "private_model_updated":False,"automatically_approved_as_professional_art":0,
        "review_status":"needs_independent_visual_approval_for_aesthetic_supervision",
        "techniques":results
    }


def run(curriculum_file:Path,benchmark_file:Path,out:Path)->dict:
    doc=json.loads(curriculum_file.read_text(encoding="utf-8"))
    bench=json.loads(benchmark_file.read_text(encoding="utf-8"))
    outcome=evaluate(doc,bench)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(outcome,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "techniques":outcome["number_of_techniques"],
        "measured":outcome["techniques_with_measured_effect"],
        "unimplemented":outcome["techniques_requiring_new_geometry"],
        "unmeasured":outcome["techniques_without_independent_measurement"]
    },indent=2))
    return outcome


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--curriculum",type=Path,required=True)
    cli.add_argument("--benchmark",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    args=cli.parse_args()
    run(args.curriculum,args.benchmark,args.out)

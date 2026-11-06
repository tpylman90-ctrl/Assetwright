"""Retain REAL 9-form-head student weights and 768 original GLB evidence.

Never overwrite prior verified original checkpoint. Preserve all three
training arms (even when research admission fails) and source lineage.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from native_multiform_student import CONDITIONS,SCHEMA,MODEL_SCHEMA
from native_multiform_acceptance import assess
from native_studied_warm_start import load_provenance

SHAPES={
    "core.0.weight":(96,1536),"core.0.bias":(96,),
    "core.2.weight":(96,96),"core.2.bias":(96,),
    "op.weight":(6,96),"op.bias":(6,),
    "strength.weight":(6,96),"strength.bias":(6,),
    "physical.weight":(6,96),"physical.bias":(6,),
    "dino.weight":(24,96),"dino.bias":(24,),
    "form.weight":(9,96),"form.bias":(9,)
}


def checksum(path:Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def weights_audit(path:Path):
    raw=path.read_bytes()
    if not 100<len(raw)<1_200_000:
        raise ValueError("Invalid original mini AI student weights size")
    size=struct.unpack("<Q",raw[:8])[0]
    if not 10<size<12000:
        raise ValueError("Original neural weights header malformed")
    header=json.loads(raw[8:8+size])
    header.pop("__metadata__",None)
    if set(header)!=set(SHAPES):
        raise ValueError("Original expanded form head architecture changed")
    buffer=memoryview(raw)[8+size:]
    spans=[]
    for key,shape in SHAPES.items():
        item=header[key]
        a,b=item["data_offsets"]
        if item.get("dtype")!="F32" or tuple(item.get("shape",[]))!=shape or (
            b-a)!=4*math.prod(shape) or a<0 or b>len(buffer):
            raise ValueError("Neural input/model tensor incompatible")
        spans.append((a,b))
        for (value,) in struct.iter_unpack("<f",buffer[a:b]):
            if not math.isfinite(value) or abs(value)>60:
                raise ValueError("Nonfinite original learned neural weight")
    spans.sort()
    if spans[0][0]!=0 or spans[-1][1]!=len(buffer) or any(
        x[1]!=y[0] for x,y in zip(spans,spans[1:])):
        raise ValueError("Original safetensors payload coverage invalid")
    return {"sha256":checksum(path),
            "parameters":sum(math.prod(shape) for shape in SHAPES.values())}


def retain(run_id:str,local:Path,original:Path,destination:Path):
    if not re.fullmatch(r"[1-9][0-9]{7,15}",run_id) or destination.exists():
        raise ValueError("Cannot overwrite immutable student learning attempt")
    parent,_,weights=load_provenance(original)
    evaluation=json.loads((local/"student"/"evaluation.json").read_text())
    geometry=json.loads((local/"forward_audit.json").read_text())
    lineage=json.loads((local/"student"/"lineage.json").read_text())
    decided=assess(evaluation,geometry,lineage)
    recorded=json.loads((local/"student"/"research_disposition.json").read_text())
    if decided!=recorded or lineage["source_parent_sha256"]!=checksum(weights):
        raise ValueError("Changed verified old student or post-hoc gate")
    new_shapes=list((local/"new"/"source").glob("*.glb"))
    if len(new_shapes)!=1088:
        raise ValueError("Source original diverse geometry school incomplete")
    for file in new_shapes:
        info=json.loads(file.with_suffix(".json").read_text())
        if (info.get("original_engine")!="AssetWright-AdvancedFormLab"
            or info.get("source_generator")!="NativeDiverseFormLab-v1"
            or info.get("source_glb_sha256")!=checksum(file)):
            raise ValueError("Original multi-form source SHA tampered")
    output_glbs=list((local/"reconstructed").glob("*.glb"))
    if len(output_glbs)!=768:
        raise ValueError("Missing all 768 independently reconstructed original GLBs")
    for file in output_glbs:
        meta=json.loads(file.with_suffix(".json").read_text())
        if (meta.get("source_engine")!="AssetWright-NativeDiverseFormLab"
            or meta.get("generated_glb_sha256")!=checksum(file)):
            raise ValueError("Student-generated native 3D surface SHA mismatch")
    candidates={}
    for condition in CONDITIONS:
        file=local/"student"/"winners"/(condition+".safetensors")
        candidates[condition]=weights_audit(file)
    if len({item["sha256"] for item in candidates.values()})!=len(CONDITIONS):
        raise ValueError("Independent trained student weights are duplicates")
    destination.mkdir(parents=True)
    for name in ("evaluation.json","lineage.json","research_disposition.json"):
        (destination/name).write_bytes((local/"student"/name).read_bytes())
    (destination/"independent_768_real_GLBS.json").write_bytes(
        (local/"forward_audit.json").read_bytes())
    for condition in CONDITIONS:
        (destination/(condition+".safetensors")).write_bytes(
            (local/"student"/"winners"/(condition+".safetensors")).read_bytes())
    record={
        "schema":"assetwright-8-original-form-neural-training-permanent-record-v6",
        "study_run_id":int(run_id),
        "parent_original_sha256":parent["saved_weights_sha256"],
        "expanded_trained_parameters":list(candidates.values())[0]["parameters"],
        "candidate_weight_sha256":{k:v["sha256"] for k,v in candidates.items()},
        "independent_validation_source_hash_sha256":
            geometry["source_hashes_sha256"],
        "original_diverse_training_and_validation_GLBS_verified":len(new_shapes),
        "real_kotlin_candidate_GLBS_verified":len(output_glbs),
        "old_original_training_lessons_replayed":1680,
        "new_original_training_lessons":672,
        "eight_actual_distinct_forms":True,
        "three_original_multi_form_models_preserved":True,
        "research_gate":decided["status"],
        "original_checkpoint_unchanged":True,
        "Android_checkpoint_installed":False,
        "human_visual_review_required":True
    }
    (destination/"learning_history.json").write_text(json.dumps(record,indent=2)+"\n")
    (destination/"RESEARCH_ONLY.md").write_text(
        "# Forge Mini v6 — real multi-form neural student archive\n\n"
        "Retains three original trained weights with a new 9-class form head "
        "(eight distinct archetypes plus legacy shell), before/after operation "
        "and continuous strength estimation. The actual source GLBs and "
        "768 independent student GLB surface comparisons were hash-verified.\n\n"
        "**Result:** "+decided["status"]+". "
        "No Android neural deployment or blind-test checkpoint selection. "
        "The old verified student remains available unchanged.\n")
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id",required=True)
    for name in ("local","original","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(retain(a.run_id,a.local,a.original,a.out),indent=2))


if __name__=="__main__":
    main()

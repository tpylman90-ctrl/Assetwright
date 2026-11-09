"""Permanent original geometry-fidelity learning without erasing old skills.

Preserves every trained ORIGINAL adapter, its original parent lineage,
all 2016 audited real Kotlin GLBs, predeclared gate and blind-source SHA.
A rejected adapter is still research; it is NEVER installed in Android.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from native_overnight_geometry_v11 import CONDITIONS,VARIANTS
from native_overnight_geometry_acceptance import assess

SHAPES={
    "hidden.0.weight":(96,204),
    "hidden.0.bias":(96,),
    "hidden.2.weight":(64,96),
    "hidden.2.bias":(64,),
    "op.weight":(6,64),
    "op.bias":(6,),
    "strength.weight":(6,64),
    "strength.bias":(6,)
}


def sha(file:Path):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def check_adapter(file:Path):
    data=file.read_bytes()
    length=struct.unpack("<Q",data[:8])[0]
    if not 10<length<10000:
        raise ValueError("Invalid original geometry adapter safetensors header")
    header=json.loads(data[8:8+length])
    header.pop("__metadata__",None)
    if set(header)!=set(SHAPES):
        raise ValueError("Original native adapter architecture was changed")
    stream=memoryview(data)[8+length:]
    chunks=[]
    for key,shape in SHAPES.items():
        item=header[key]
        a,b=item["data_offsets"]
        if (item.get("dtype")!="F32"
            or tuple(item.get("shape",()))!=shape
            or b-a!=4*math.prod(shape)
            or a<0 or b>len(stream)):
            raise ValueError("Native learned geometry tensor is malformed")
        chunks.append((a,b))
        for (number,) in struct.iter_unpack("<f",stream[a:b]):
            if not math.isfinite(number) or abs(number)>80:
                raise ValueError("Non-finite original learned native neural weight")
    chunks.sort()
    if (chunks[0][0]!=0 or chunks[-1][1]!=len(stream)
        or any(x[1]!=y[0] for x,y in zip(chunks,chunks[1:]))):
        raise ValueError("Native adapted neural payload did not cover its tensors")
    return {
        "sha256":sha(file),
        "parameters":sum(math.prod(dims) for dims in SHAPES.values())
    }


def retain(run_id,workspace:Path,v6:Path,v7:Path,v8:Path,v9:Path,v10:Path,dest:Path):
    if (not re.fullmatch(r"[1-9][0-9]{7,15}",run_id)
        or dest.exists()):
        raise ValueError("Immutable genuine learning attempt cannot be overwritten")
    research=workspace/"student"
    evaluation=json.loads((research/"evaluation.json").read_text())
    geometry=json.loads((workspace/"forward_audit.json").read_text())
    lineage=json.loads((research/"lineage.json").read_text())
    verdict=assess(evaluation,geometry,lineage)
    saved=json.loads((research/"research_disposition.json").read_text())
    if verdict!=saved:
        raise ValueError("Actual form fidelity gate disagrees with saved disposition")
    initial6=v6/"balanced_forms.safetensors"
    initial7=v7/"hard_form_distinctions.safetensors"
    continued8=v8/"hard_physical.safetensors"
    frozen9=v9/"replay_continuation.safetensors"
    continued10=v10/"warm_replay.safetensors"
    history10=json.loads((v10/"learning_history.json").read_text())
    if history10["trained_adapters"]["warm_replay"]["sha256"]!=sha(continued10):
        raise ValueError("Original research-only v10 checkpoint changed")
    for actual,expected in (
        (initial6,lineage["source_v6_weight_sha256"]),
        (initial7,lineage["source_v7_form_weight_sha256"]),
        (continued8,lineage["source_v8_adapter_sha256"]),
        (frozen9,lineage["source_v9_identity_sha256"]),
        (continued10,lineage["source_v10_adapter_sha256"])):
        if sha(actual)!=expected:
            raise ValueError("Prior saved source-hashed native learned weights changed")
    glbs=list((workspace/"new"/"source").glob("*.glb"))
    if len(glbs)!=1808:
        raise ValueError("Original new 1808-GLB source school incomplete")
    for file in glbs:
        info=json.loads(file.with_suffix(".json").read_text())
        if (info.get("source_generator")!="NativeDiverseFormLab-v1"
            or info.get("source_glb_sha256")!=sha(file)):
            raise ValueError("Original native geometry source GLB changed")
    generated=list((workspace/"reconstructed").glob("*.glb"))
    if len(generated)!=2016:
        raise ValueError("Original student 2016 GLBs were not completed")
    for file in generated:
        meta=json.loads(file.with_suffix(".json").read_text())
        if (meta.get("source_engine")!="AssetWright-NativeDiverseFormLab"
            or meta.get("generated_glb_sha256")!=sha(file)):
            raise ValueError("Reconstructed original native GLB changed")
    candidates={
        condition:check_adapter(research/"winners"/(condition+".safetensors"))
        for condition in VARIANTS[1:]
    }
    if len({c["sha256"] for c in candidates.values()})!=6:
        raise ValueError("Six original sequential trained adapters contain duplicate weights")
    dest.mkdir(parents=True)
    for filename in ("evaluation.json","lineage.json","research_disposition.json"):
        (dest/filename).write_bytes((research/filename).read_bytes())
    (dest/"independent_2016_Kotlin_GLBS.json").write_bytes(
        (workspace/"forward_audit.json").read_bytes())
    for condition in VARIANTS[1:]:
        (dest/(condition+".safetensors")).write_bytes(
            (research/"winners"/(condition+".safetensors")).read_bytes())
    report={
        "schema":"assetwright-durable-original-form-fidelity-research-v11",
        "run_id":int(run_id),
        "parent_v6_action_strength_sha256":sha(initial6),
        "parent_v7_shape_identity_sha256":sha(initial7),
        "continued_original_v8_adapter_sha256":sha(continued8),
        "frozen_original_v9_form_head_sha256":sha(frozen9),
        "frozen_original_models_preserved":True,
        "source_original_Kotlin_GLBS_verified":len(glbs),
        "generated_original_Kotlin_GLBS_verified":len(generated),
        "old_correct_original_geometry_replay_examples":1152,
        "new_original_geometry_training_examples":1152,
        "new_distinct_blind_source_families":16,
        "blind_original_source_sha256":geometry["source_hashes_sha256"],
        "actual_optimizer_seconds":evaluation["measured_optimizer_seconds"],
        "trained_adapters":candidates,
        "continued_original_v10_adapter_sha256":sha(continued10),
        "sequential_900_second_stages":6,
        "research_gate":verdict["status"],
        "production_checkpoint_modified":False,
        "Android_neural_deployed":False
    }
    (dest/"learning_history.json").write_text(json.dumps(report,indent=2)+"\n")
    (dest/"RESEARCH_ONLY.md").write_text(
        "# Original Forge Mini v11 form-conditioned geometry fidelity\n\n"
        "Preserves six consecutive 900-second original neural stage checkpoints "
        "across two equal-budget paths, frozen earlier action/shape model "
        "hashes, 1,152 old TRAIN-only replay + 1,152 new original "
        "geometry examples, and an independent 2,016-GLB blind 3D surface "
        "audit across eight real source form archetypes.\n\n"
        "**Research verdict:** "+verdict["status"]+". "
        "No Android neural checkpoint was installed. Even research eligibility "
        "requires separate visual review before any practical deployment.\n")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id",required=True)
    for name in ("workspace","v6","v7","v8","v9","v10","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(retain(a.run_id,a.workspace,a.v6,a.v7,a.v8,a.v9,a.v10,a.out),indent=2))


if __name__=="__main__":
    main()

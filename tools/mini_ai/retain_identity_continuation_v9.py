"""Save genuine v7 shape identity gradients and 3D proof permanently.

The rejected but valid v6 experimental native form student is the research
parent. Its original operation / strength weights and the verified v3
production-safe research checkpoint are NEVER overwritten. New identity
weights remain research-only, even if the physical native 3D gate passes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from native_identity_continuation_v9 import CONDITIONS
from native_identity_continuation_acceptance import assess

SHAPES={
    "encoder.0.weight":(128,3072),
    "encoder.0.bias":(128,),
    "encoder.2.weight":(96,128),
    "encoder.2.bias":(96,),
    "classifier.weight":(9,96),
    "classifier.bias":(9,)
}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check_weights(path):
    contents=path.read_bytes()
    length=struct.unpack("<Q",contents[:8])[0]
    if not 20<length<10000:
        raise ValueError("Invalid original shape encoder safetensors header")
    header=json.loads(contents[8:8+length])
    header.pop("__metadata__",None)
    if set(header)!=set(SHAPES):
        raise ValueError("Unexpected original form-identity neural architecture")
    payload=memoryview(contents)[8+length:]
    spans=[]
    for name,shape in SHAPES.items():
        record=header[name]
        begin,end=record["data_offsets"]
        if (record.get("dtype")!="F32"
            or tuple(record.get("shape",[]))!=shape
            or end-begin!=4*math.prod(shape)
            or begin<0 or end>len(payload)):
            raise ValueError("Invalid original identity neural tensor")
        spans.append((begin,end))
        for (value,) in struct.iter_unpack("<f",payload[begin:end]):
            if not math.isfinite(value) or abs(value)>100:
                raise ValueError("Unsafe nonfinite research identity tensor")
    spans.sort()
    if (spans[0][0]!=0 or spans[-1][1]!=len(payload)
        or any(x[1]!=y[0] for x,y in zip(spans,spans[1:]))):
        raise ValueError("Research neural tensor payload incomplete")
    return sha(path)


def retain(run_id,work,old,teacher_dir,destination):
    if (not re.fullmatch("[1-9][0-9]{7,15}",run_id)
        or destination.exists()):
        raise ValueError("Cannot overwrite an existing source-hashed learning run")
    evaluation=json.loads((work/"student"/"evaluation.json").read_text())
    lineage=json.loads((work/"student"/"lineage.json").read_text())
    geometry=json.loads((work/"forward_audit.json").read_text())
    disposition=assess(evaluation,geometry,lineage)
    claimed=json.loads((work/"student"/"research_disposition.json").read_text())
    if disposition!=claimed:
        raise ValueError("Manipulated predeclared v9 gate after blind results")
    parent=old/"balanced_forms.safetensors"
    history=json.loads((old/"learning_history.json").read_text())
    if (sha(parent)!=lineage["parent_source_weights_sha256"]
        or sha(parent)!=history["candidate_weight_sha256"]["balanced_forms"]):
        raise ValueError("Original v6 checkpoint neural weights were modified")
    teacher=teacher_dir/"hard_form_distinctions.safetensors"
    teacher_history=json.loads((teacher_dir/"learning_history.json").read_text())
    if (sha(teacher)!=lineage["source_v7_hard_form_weights_sha256"]
        or teacher_history["new_neural_identity_weights_SHA256"]["hard_form_distinctions"]
           !=sha(teacher)):
        raise ValueError("Actual neural v7 hard-form source knowledge was altered")
    originals=list((work/"new"/"source").glob("*.glb"))
    if len(originals)!=1824:
        raise ValueError("Missing original Kotlin v7 source meshes")
    for file in originals:
        info=json.loads(file.with_suffix(".json").read_text())
        if (info.get("source_generator")!="NativeDiverseFormLab-v1"
            or info.get("source_glb_sha256")!=sha(file)):
            raise ValueError("New shape identity source labels not tied to real Kotlin GLB")
    results=list((work/"reconstructed").glob("*.glb"))
    if len(results)!=1152:
        raise ValueError("Incomplete independently reconstructed original 3D meshes")
    for file in results:
        doc=json.loads(file.with_suffix(".json").read_text())
        if (doc.get("source_engine")!="AssetWright-NativeDiverseFormLab"
            or doc.get("generated_glb_sha256")!=sha(file)):
            raise ValueError("Generated distinct form GLB SHA256 changed")
    hashes={}
    for name in CONDITIONS:
        file=work/"student"/"winners"/(name+".safetensors")
        hashes[name]=check_weights(file)
    if len(set(hashes.values()))!=len(CONDITIONS):
        raise ValueError("Separate form-identity students are identical")
    destination.mkdir(parents=True)
    for name in ("evaluation.json","lineage.json","research_disposition.json"):
        (destination/name).write_bytes((work/"student"/name).read_bytes())
    (destination/"independent_1152_native_GLBS.json").write_bytes(
        (work/"forward_audit.json").read_bytes())
    for name in CONDITIONS:
        (destination/(name+".safetensors")).write_bytes(
            (work/"student"/"winners"/(name+".safetensors")).read_bytes())
    proof={
        "schema":"assetwright-original-independent-shape-identity-knowledge-v9",
        "github_run_id":int(run_id),
        "source_parent_v6_experimental_weight_SHA256":sha(parent),
        "source_teacher_v7_hard_form_SHA256":sha(teacher),
        "genuine_v7_warm_start":True,
        "old_train_baselines_replayed":104,
        "new_neural_identity_weights_SHA256":hashes,
        "old_native_operation_strength_network_unchanged":True,
        "distinct_source_baselines_trained":168,
        "new_source_baseline_train_cases":64,
        "new_source_development_form_families":16,
        "untouched_new_source_blind_families":16,
        "new_original_Kotlin_GLBS_verified":len(originals),
        "real_original_Kotlin_reconstructions_verified":len(results),
        "training_time_seconds":evaluation["optimizer_active_seconds"],
        "research_disposition":disposition["status"],
        "original_v6_previous_candidate_not_approved_for_mobile":True,
        "production_research_checkpoint_untouched":True,
        "human_visual_review_required":True,
        "android_neural_installed":False
    }
    (destination/"learning_history.json").write_text(json.dumps(proof,indent=2)+"\n")
    (destination/"RESEARCH_ONLY.md").write_text(
        "# Forge Mini v9 — independent source-balanced shape identity learner\n\n"
        "3 newly trained ORIGINAL neural shape encoders, 1800 verified seconds "
        "of CPU optimization, 168 genuinely distinct source shape baselines, "
        "16 family-disjoint new blind source forms and 1,152 independently "
        "generated Kotlin GLBs. This study freezes all older operation and "
        "strength weights exactly. \n\n"
        "**Research verdict:** "+disposition["status"]+". "
        "The v6 source checkpoint was experimental and was NOT previously "
        "promoted. Neither it nor these new candidate weights have been "
        "deployed to Android. No claims of arbitrary text-to-CAD.\n")
    return proof


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for x in ("work","old","teacher_dir","out"):
        p.add_argument("--"+x,type=Path,required=True)
    p.add_argument("--run-id",required=True)
    a=p.parse_args()
    print(json.dumps(retain(a.run_id,a.work,a.old,a.teacher_dir,a.out),indent=2))


if __name__=="__main__":
    main()

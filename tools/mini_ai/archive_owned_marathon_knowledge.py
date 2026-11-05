"""Freeze the best teacher-FREE original Mini AI student as reusable knowledge.

This is not automatic research promotion to Android. The frozen weights are
source-hashed and available to the next explicitly designed learning loop,
instead of being discarded with the 45-day GitHub Actions ZIP.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

RUN=42080318206
ARTIFACT="assetwright-32minute-DINO-training-and-192-GLB-results"
SOURCE_ARTIFACT="assetwright-marathon-888-own-GLBs-and-teacher"
SOURCE_COMMIT="38d5780adaa20a342546f514ecf8cbc8045a142f"
TARGET=Path("training/knowledge/native_strength_teacher_free_42080318206")
SHAPES={
    "core.0.weight":[96,1536],
    "core.0.bias":[96],
    "core.2.weight":[96,96],
    "core.2.bias":[96],
    "op.weight":[6,96],
    "op.bias":[6],
    "strength.weight":[6,96],
    "strength.bias":[6],
    "physical.weight":[6,96],
    "physical.bias":[6],
    "dino.weight":[24,96],
    "dino.bias":[24],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_weights(path):
    raw=path.read_bytes()
    if len(raw)<100 or len(raw)>2_000_000:
        raise ValueError("Unexpected original student checkpoint byte length")
    header_bytes=struct.unpack("<Q",raw[:8])[0]
    if not 10<header_bytes<12000:
        raise ValueError("Unsafe original safetensors header")
    header=json.loads(raw[8:8+header_bytes])
    header.pop("__metadata__",None)
    if set(header)!=set(SHAPES):
        raise ValueError("Incomplete or unexpected original Mini AI parameters")
    payload=memoryview(raw)[8+header_bytes:]
    coverage=[]
    for key,shape in SHAPES.items():
        item=header[key]
        if item.get("dtype")!="F32" or item.get("shape")!=shape:
            raise ValueError("Invalid model parameter type or shape "+key)
        start,end=item["data_offsets"]
        size=math.prod(shape)*4
        if start<0 or end-start!=size or end>len(payload):
            raise ValueError("Invalid model tensor payload "+key)
        for (value,) in struct.iter_unpack("<f",payload[start:end]):
            if not math.isfinite(value) or abs(value)>50:
                raise ValueError("Non-finite or excessive original trained weight")
        coverage.append((start,end))
    coverage.sort()
    if coverage[0][0]!=0 or coverage[-1][1]!=len(payload) or any(
        a[1]!=b[0] for a,b in zip(coverage,coverage[1:])):
        raise ValueError("Overlapping/fragmented original model tensors")
    return {"sha256":digest(path),"byte_length":len(raw),
            "tensors":len(SHAPES),
            "parameter_count":sum(math.prod(s) for s in SHAPES.values())}


def preserve(source,outputs,folder):
    evaluation=json.loads((outputs/"student"/"evaluation.json").read_text())
    forward=json.loads((outputs/"forward_audit.json").read_text())
    guided=json.loads((outputs/"student"/"candidate_student.json").read_text())
    disposition=json.loads((outputs/"student"/"combined_disposition.json").read_text())
    if (evaluation.get("schema")!="assetwright-32min-strength-student-evaluation-v3"
        or evaluation.get("study")!="strength_marathon_v3"
        or evaluation.get("train_examples")!=672
        or evaluation.get("development_examples")!=96
        or evaluation.get("untouched_holdout_examples")!=96
        or evaluation.get("completed_independent_training_sessions")!=16
        or evaluation.get("verified_active_training_seconds",0)<1800
        or forward.get("study_id")!="strength_marathon_v3"
        or forward.get("all_native_glbs_structurally_audited") is not True
        or disposition.get("status")!="research_candidate_rejected"):
        raise ValueError("Source results or honest nonpromotion conclusion invalid")
    if guided.get("android_deployable") is not False or guided.get("teacher_generates_geometry") is not False:
        raise ValueError("Unapproved external or Android research promotion")
    control=evaluation["heldout"]["teacher_free"]
    forward_control=forward["paired_teacher_free"]
    if (control["accuracy"]<.90 or control["strength_mae"]>.14
        or forward_control["mean_normalized_vertex_rmse"]>=.005
        or abs(control["accuracy"]-forward_control["operation_accuracy"])>1e-5
        or abs(control["strength_mae"]-forward_control["strength_mae"])>.0002):
        raise ValueError("Owned teacher-free student does not meet independent frozen criteria")
    history=evaluation["all_session_development_results"]
    winner=history["teacher_free_winner_seed"]
    selected=[x for x in history["teacher_free"] if x["seed"]==winner]
    if len(selected)!=1 or len(history["teacher_free"])!=8:
        raise ValueError("Source winner not selected independently on development families")
    filename=f"teacher_free__seed_{winner}.safetensors"
    if selected[0].get("checkpoint")!=filename:
        raise ValueError("Winner checkpoint identity mismatch")
    weights=outputs/"student"/"seed_checkpoints"/filename
    checks=audit_weights(weights)

    cases=forward.get("cases")
    if not isinstance(cases,list) or len(cases)!=96:
        raise ValueError("Independent source-target audit missing")
    source_hashes={x["case"]:x["source_glb_sha256"] for x in cases}
    if len(source_hashes)!=96:
        raise ValueError("Repeated heldout original GLB")
    summary_hash=hashlib.sha256("\n".join(sorted(source_hashes.values())).encode()).hexdigest()
    if (summary_hash!=evaluation.get("source_validation_hashes_sha256")
        or summary_hash!=forward.get("source_hashes_sha256")
        or summary_hash!=guided.get("blind_source_hashes_sha256")):
        raise ValueError("Untouched native source cohort not aligned")
    originals=list((source/"source").glob("*.glb"))
    if len(originals)!=888:
        raise ValueError("Missing archived original native source corpus")
    for file in originals:
        info=json.loads(file.with_suffix(".json").read_text())
        if info.get("source_glb_sha256")!=digest(file):
            raise ValueError("Original Kotlin mesh changed since DINO training")
    reconstructed=list((outputs/"reconstructed").glob("*.glb"))
    if len(reconstructed)!=192:
        raise ValueError("Incomplete original Kotlin student mesh reconstruction cohort")
    for item in cases:
        p=outputs/"reconstructed"/(item["case"]+"__teacher_free.glb")
        data=json.loads(p.with_suffix(".json").read_text())
        if (data.get("reference_glb_sha256")!=item["source_glb_sha256"] or
            data.get("generated_glb_sha256")!=digest(p) or
            data.get("source_engine")!="AssetWright-AdvancedFormLab"):
            raise ValueError("Original verified teacher-free prediction hash mismatch")
    if folder.exists():
        raise ValueError("Research knowledge already archived; refuse overwrite")
    folder.mkdir(parents=True)
    (folder/"owned_native_student.safetensors").write_bytes(weights.read_bytes())
    normalization={
        "schema":"assetwright-native-student-normalization-v1",
        "input_feature_dim":guided["input_feature_dim"],
        "hidden_dim":guided["model_hidden_dim"],
        "supported_ops":guided["supported_ops"],
        "train_feature_mean":guided["train_feature_mean"],
        "train_feature_std":guided["train_feature_std"],
        "train_morph_std":guided["train_morph_std"],
        "input":"two-view fixed camera original native before-after pixels",
        "weights_selection":"teacher_free model, selected on development only",
    }
    (folder/"normalization.json").write_text(json.dumps(normalization,separators=(",",":"))+"\n")
    provenance={
        "schema":"assetwright-permanent-original-mini-native-knowledge-v1",
        "research_run_id":RUN,
        "source_commit_sha":SOURCE_COMMIT,
        "source_artifacts":[ARTIFACT,SOURCE_ARTIFACT],
        "student":"original from-scratch teacher-free native geometry",
        "condition":"teacher_free",
        "selected_seed":winner,
        "development_selected_checkpoint":selected[0]["selected_dev_step"],
        "saved_weights_sha256":checks["sha256"],
        "parameter_count":checks["parameter_count"],
        "original_source_GLBS_verified":len(originals),
        "new_native_reconstructions_verified":len(reconstructed),
        "heldout_count":96,
        "heldout_source_digest":summary_hash,
        "heldout_operation_accuracy":control["accuracy"],
        "heldout_strength_mae":control["strength_mae"],
        "heldout_true_GLb_vertex_RMSE":forward_control["mean_normalized_vertex_rmse"],
        "teacher_used_for_student":False,
        "external_3d_generator_used":False,
        "android_installed":False,
        "approved_for_production":False,
        "review_status":"research_verified_human_review_pending",
        "validation_cohort":"exposed_retired_do_not_reuse_as_blind",
        "next_usage":"explicit warm-start with old-train replay and NEW independent heldout families"
    }
    (folder/"model_lineage.json").write_text(json.dumps(provenance,indent=2)+"\n")
    (folder/"RESEARCH_ONLY.md").write_text(
        "# Persistent Forge Mini original geometry knowledge\n\n"
        "Retains real trained weights, not only benchmark scores. This is the"
        " teacher-FREE student from the 32-minute study, validated on native"
        " Kotlin GLB reconstructions; DINO-assisted candidate remains rejected."
        "\n\nThis archive is **NOT loaded in Android**. Before on-device use,"
        " implement and verify a compatible pixel pipeline and human review."
        " Do not reuse the retired heldout source shapes for further tuning."
        "\n\nNext research should warm-start these exact weights, replay"
        " prior training examples to avoid forgetting, and evaluate with"
        " new source families.\n")
    return provenance


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--results",type=Path,required=True)
    p.add_argument("--out",type=Path,default=TARGET)
    a=p.parse_args()
    print(json.dumps(preserve(a.source,a.results,a.out),indent=2))


if __name__=="__main__":
    main()

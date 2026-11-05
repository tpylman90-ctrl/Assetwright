"""Durably commit all 3 real original geometry student candidates + evidence.

A success-status workflow is not scientific permission to deploy.
Even a rejected attempt retains learned neural weights for research;
the original verified prior checkpoint is never overwritten.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

from archive_owned_marathon_knowledge import audit_weights
from native_studied_warm_start import load_provenance
from native_geometry_aware_acceptance import reconcile
from native_geometry_aware_student import CONDITIONS


def digest(file:Path)->str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def retain(run_id:str,local:Path,original:Path,permanent:Path):
    if not re.fullmatch(r"[1-9][0-9]{7,15}",run_id):
        raise ValueError("GitHub Actions run ID must be authentic")
    if permanent.exists():
        raise ValueError("Prevent repeated overwriting of retained neural learning")
    parent,_,saved=load_provenance(original)
    result=json.loads((local/"student"/"evaluation.json").read_text())
    lineage=json.loads((local/"student"/"lineage.json").read_text())
    geometry=json.loads((local/"forward_audit.json").read_text())
    disposition=reconcile(result,geometry,lineage)
    claimed=json.loads((local/"student"/"research_disposition.json").read_text())
    if claimed!=disposition:
        raise ValueError("Research conclusion cannot be rewritten after validation")
    if (disposition["parent_checkpoint_sha256"]!=digest(saved)
        or parent["saved_weights_sha256"]!=digest(saved)):
        raise ValueError("Existing original learned knowledge was modified")
    new_source=local/"new"/"source"
    verified=set()
    for glb in new_source.glob("*.glb"):
        info=json.loads(glb.with_suffix(".json").read_text())
        sha=digest(glb)
        if (info.get("original_engine")!="AssetWright-AdvancedFormLab"
            or info.get("source_glb_sha256")!=sha or sha in verified):
            raise ValueError("Tampered/repeated original new Kotlin training GLB")
        verified.add(sha)
    if len(verified)!=716:
        raise ValueError("Missing novel original train/development/validation geometry")
    built=list((local/"reconstructed").glob("*.glb"))
    if len(built)!=384:
        raise ValueError("Not all actual predicted 3D meshes were rebuilt")
    for glb in built:
        info=json.loads(glb.with_suffix(".json").read_text())
        if (info.get("source_engine")!="AssetWright-AdvancedFormLab"
            or info.get("generated_glb_sha256")!=digest(glb)):
            raise ValueError("Reconstructed original GLB hash mismatch")
    weights={}
    for name in CONDITIONS:
        source=local/"student"/"winners"/(name+".safetensors")
        summary=audit_weights(source)
        if summary["parameter_count"]!=parent["parameter_count"]:
            raise ValueError("Native original student architecture was replaced")
        weights[name]=summary["sha256"]
    if len(set(weights.values()))!=len(weights):
        raise ValueError("Equal-budget candidates are identical: fake independent training")
    permanent.mkdir(parents=True)
    copied={
        "evaluation.json":local/"student"/"evaluation.json",
        "training_lineage.json":local/"student"/"lineage.json",
        "research_disposition.json":local/"student"/"research_disposition.json",
        "independent_384_GLBS.json":local/"forward_audit.json"
    }
    for target,source in copied.items():
        (permanent/target).write_bytes(source.read_bytes())
    for name in CONDITIONS:
        (permanent/(name+".safetensors")).write_bytes(
            (local/"student"/"winners"/(name+".safetensors")).read_bytes())
    history={
        "schema":"assetwright-native-3d-deep-learning-permanent-history-v5",
        "run_id":int(run_id),
        "original_model_sha256":digest(saved),
        "new_model_sha256":weights,
        "source_hashes_sha256":geometry["source_hashes_sha256"],
        "original_v5_GLBS_audited":len(verified),
        "old_train_examples_replayed":1176,
        "new_train_examples":504,
        "new_development_only_cases":96,
        "fresh_blind_GLBS":96,
        "original_reconstructions_verified":len(built),
        "genuine_trained_safetensors_per_condition":True,
        "same_original_start":True,
        "training_time_seconds":result["actual_training_optimizer_seconds"],
        "preselected_dev_winner":disposition["selected_condition"],
        "independent_real_3D_gain_vs_parent":disposition["real_3D_gain_vs_parent_fraction"],
        "disposition":disposition["disposition"],
        "prior_original_model_unmodified":True,
        "new_weights_production_enabled":False,
        "human_visual_review_required":True
    }
    (permanent/"learning_history.json").write_text(json.dumps(history,indent=2)+"\n")
    (permanent/"RESEARCH_ONLY.md").write_text(
        "# Geometry-aware original Forge Mini cumulative learning v5\n\n"
        "All 3 REAL neural checkpoints and 30 minutes of training are preserved. "
        "The parent retained model remains immutable. Independent evaluation "
        "compared 384 real Kotlin GLBs from 96 fresh, never-inspected sources.\n\n"
        "**Gate:** "+disposition["disposition"]+". "
        "A successful GitHub workflow does not prove a better 3D model. "
        "No automatic Android installation, and no automatic production "
        "checkpoint replacement. A passing research result still requires "
        "human visual review.\n\n"
        "Retired v5 blind source families must never be reused for future "
        "model tuning or source-family development.\n")
    return history


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("local","original","permanent"):
        p.add_argument("--"+field,type=Path,required=True)
    p.add_argument("--run-id",required=True)
    a=p.parse_args()
    print(json.dumps(retain(a.run_id,a.local,a.original,a.permanent),indent=2))


if __name__=="__main__":
    main()

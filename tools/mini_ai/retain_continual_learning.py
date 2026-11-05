"""Commit every verified real training attempt without overwriting champion.

Once training has actually completed, store its updated original weights and
full lineage in git. A candidate that fails regression is still archived as
an honest experiment but NEVER becomes the active/recommended successor.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

from archive_owned_marathon_knowledge import audit_weights
from native_continual_acceptance import assess
from native_studied_warm_start import load_provenance


def store(folder:Path,run_id:str,root:Path,knowledge:Path):
    if not re.fullmatch(r"[1-9][0-9]{7,15}",run_id):
        raise ValueError("Invalid exact GitHub Actions run identifier")
    if root.exists():
        raise ValueError("Original training attempt is already preserved")
    student=folder/"student"
    evaluation=json.loads((student/"evaluation.json").read_text())
    geometry=json.loads((folder/"forward_audit.json").read_text())
    lineage=json.loads((student/"candidate_lineage.json").read_text())
    disposition=assess(evaluation,geometry,lineage)
    recorded=json.loads((student/"combined_disposition.json").read_text())
    if recorded!=disposition:
        raise ValueError("Stored research gate is not reproducible")
    parent,_,_=load_provenance(knowledge)
    if parent["saved_weights_sha256"]!=disposition["prior_checkpoint_sha256"]:
        raise ValueError("Source-hashed old learned checkpoint changed")
    candidate=student/"continued_candidate.safetensors"
    checks=audit_weights(candidate)
    if checks["parameter_count"]!=parent["parameter_count"]:
        raise ValueError("New student lost original native network architecture")
    original_glbs=list((folder/"new"/"source").glob("*.glb"))
    if len(original_glbs)!=716:
        raise ValueError("Incomplete new 716-Kotlin-GLB cumulative training school")
    source_hashes=set()
    for file in original_glbs:
        meta=json.loads(file.with_suffix(".json").read_text())
        digest=hashlib.sha256(file.read_bytes()).hexdigest()
        if (meta.get("source_glb_sha256")!=digest or
            meta.get("original_engine")!="AssetWright-AdvancedFormLab" or
            digest in source_hashes):
            raise ValueError("New original Kotlin sources not independently retained")
        source_hashes.add(digest)
    regenerated=list((folder/"reconstructed").glob("*.glb"))
    if len(regenerated)!=192:
        raise ValueError("Missing newly reconstructed native source geometry")
    for file in regenerated:
        metadata=json.loads(file.with_suffix(".json").read_text())
        if (metadata.get("generated_glb_sha256")!=hashlib.sha256(
                file.read_bytes()).hexdigest() or
            metadata.get("source_engine")!="AssetWright-AdvancedFormLab"):
            raise ValueError("New native GLB reconstructed SHA changed")
    root.mkdir(parents=True)
    (root/"updated_original_student.safetensors").write_bytes(candidate.read_bytes())
    for name,target in (
        ("evaluation.json","evaluation.json"),
        ("candidate_lineage.json","candidate_lineage.json"),
        ("predictions.json","predictions.json")):
        (root/target).write_bytes((student/name).read_bytes())
    (root/"independent_forward_geometry.json").write_bytes(
        (folder/"forward_audit.json").read_bytes())
    (root/"research_disposition.json").write_text(
        json.dumps(disposition,indent=2)+"\n")
    record={
        "schema":"assetwright-original-continual-learning-persistent-run-v4",
        "github_actions_run":int(run_id),
        "source_study":"strength_continual_v4",
        "parent_original_sha256":parent["saved_weights_sha256"],
        "child_trained_weights_sha256":checks["sha256"],
        "parameter_count":checks["parameter_count"],
        "rehearsed_earlier_training_examples":672,
        "new_training_examples":504,
        "new_development_examples":96,
        "fresh_blind_original_targets":96,
        "original_Kotlin_GLBS_verified":716,
        "actual_student_GLBS_verified":192,
        "heldout_sha256":disposition["new_candidate_source_hash"],
        "independent_geometry_improvement":disposition["real_geometry_improvement_fraction"],
        "learned_successor_research_eligible":
            disposition["status"]=="eligible_for_human_research_review",
        "parent_checkpoint_immutable":True,
        "candidate_remains_available_for_future_comparisons":True,
        "Android_installed":False,
        "human_visual_review_required":True
    }
    (root/"learning_lineage.json").write_text(json.dumps(record,indent=2)+"\n")
    (root/"RESEARCH_ONLY.md").write_text(
        "# Persistent original Forge Mini learning attempt "+run_id+"\n\n"
        "Contains real updated neural weights, prior checkpoint lineage, "
        "672 old replay examples and 504 new training examples, plus "
        "96 fresh native GLB validation cases and 192 source-audited "
        "reconstruction results.\n\n"
        "**Disposition:** "+disposition["status"]+". "
        "A rejected candidate remains readable as a learning experiment "
        "but must NOT replace the original verified research checkpoint. "
        "A positive decision is research-eligible for human review ONLY, "
        "not a mobile deployment.\n\n"
        "The prior checkpoint and Android production app were not changed.\n")
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id",required=True)
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--knowledge",required=True,type=Path)
    a=p.parse_args()
    result=store(a.root,a.run_id,a.out,a.knowledge)
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()

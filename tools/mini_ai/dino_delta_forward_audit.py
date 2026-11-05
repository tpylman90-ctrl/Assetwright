"""Audit source-matched native Kotlin BEFORE/AFTER reconstructed GLBs.

Compares the actual indexed vertex buffers, never filenames as geometric
features. A structurally sound mesh is not automatically good/approved geometry.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from dino_delta_school import STUDY,FAMILIES,expected_changes,read_case
from dino_native_forward_audit import audited,distance

SCHEMA="assetwright-native-before-after-reconstruction-v1"
VARIANTS=("teacher_free","DINO_guided")


def forward(source:Path,reconstructed:Path)->dict:
    cases={stem:identity for stem,identity in expected_changes().items()
           if identity[0]=="validation"}
    expected={stem+"__"+variant for stem in cases for variant in VARIANTS}
    found={p.stem for p in reconstructed.glob("*.glb")}
    meta_found={p.stem for p in reconstructed.glob("*.json")}
    if len(cases)!=(96 if STUDY=="strength_v2" else 54) or found!=expected or meta_found!=expected:
        raise ValueError("Incomplete or contaminated native after/before reconstruction cohort")
    records=[];by_op=defaultdict(list);all_target_hashes=[]
    for stem,identity in sorted(cases.items()):
        split,family,op,strength,base=identity
        target=source/(stem+".glb")
        untouched=source/(base+".glb")
        original=read_case(source,stem,identity[:4],baseline=False)
        baseline=read_case(source,base,(split,family,"BASELINE",0.),baseline=True)
        if audited(target)["model_sha256"]!=original["source_sha256"]:
            raise ValueError("Original target topology not valid")
        if audited(untouched)["model_sha256"]!=baseline["source_sha256"]:
            raise ValueError("Native original baseline topology not valid")
        all_target_hashes.append(original["source_sha256"])
        result={
            "case":stem,"family":family,"target_operation":op,
            "target_strength":strength,
            "source_glb_sha256":original["source_sha256"],
            "baseline_glb_sha256":baseline["source_sha256"],
            "unchanged_native_rmse":distance(target,untouched)
        }
        for variant in VARIANTS:
            path=reconstructed/(stem+"__"+variant+".glb")
            audit=audited(path)
            meta=json.loads(path.with_suffix(".json").read_text())
            if not (
                meta.get("schema")==SCHEMA and meta.get("case")==stem
                and meta.get("variant")==variant
                and meta.get("source_engine")=="AssetWright-AdvancedFormLab"
                and meta.get("reference_glb_sha256")==original["source_sha256"]
                and meta.get("baseline_glb_sha256")==baseline["source_sha256"]
                and meta.get("generated_glb_sha256")==audit["model_sha256"]
            ):
                raise ValueError("Student reconstruction/source GLB provenance mismatch")
            prediction=meta.get("chosen_operation")
            if prediction not in ("SECTION_LOFT","TANGENT_SWEEP",
                "SECTION_TWIST","SUPERELLIPSE_PROFILE","LOWER_RECESS",
                "RIBBED_FAIRING"):
                raise ValueError("Unknown native construction prediction")
            predicted_strength=meta.get("chosen_strength")
            if type(predicted_strength) not in (float,int) or not 0<=predicted_strength<=1:
                raise ValueError("Invalid native strength output")
            result[variant]={
                "operation":prediction,"strength":predicted_strength,
                "correct_operation":prediction==op,
                "strength_error":abs(predicted_strength-strength),
                "normalized_vertex_rmse":distance(target,path),
                "source_sha256":audit["model_sha256"],
                "triangles":audit["triangles"]
            }
        records.append(result)
        by_op[op].append(result)

    def measure(variant):
        n=len(records)
        return {
            "operation_accuracy":sum(r[variant]["correct_operation"] for r in records)/n,
            "strength_mae":sum(r[variant]["strength_error"] for r in records)/n,
            "mean_normalized_vertex_rmse":sum(r[variant]["normalized_vertex_rmse"] for r in records)/n
        }
    nochange=sum(r["unchanged_native_rmse"] for r in records)/len(records)
    paired=measure("teacher_free")
    guided=measure("DINO_guided")
    if nochange<=0 or paired["mean_normalized_vertex_rmse"]<=0:
        raise ValueError("Unphysical native reconstruction error")
    improvement_over_nochange=(nochange-guided["mean_normalized_vertex_rmse"])/nochange
    improvement_vs_paired=(paired["mean_normalized_vertex_rmse"]-
                           guided["mean_normalized_vertex_rmse"])/paired["mean_normalized_vertex_rmse"]
    per_operation={
        op:{
            "examples":len(rows),
            "teacher_guided_correct":sum(r["DINO_guided"]["correct_operation"] for r in rows),
            "paired_only_correct":sum(r["teacher_free"]["correct_operation"] for r in rows),
            "mean_guided_vertex_rmse":sum(r["DINO_guided"]["normalized_vertex_rmse"]
                                         for r in rows)/len(rows)
        } for op,rows in by_op.items()
    }
    checks={
        "all_real_generated_meshes_manifold":True,
        "guided_operation_accuracy_ge_0_60":guided["operation_accuracy"]>=.60,
        "guided_strength_mae_le_0_18":guided["strength_mae"]<=.18,
        "beats_unchanged_native_by_10_percent":improvement_over_nochange>=.10,
        "beats_equivalent_paired_without_DINO_by_2_percent":improvement_vs_paired>=.02
    }
    return {
        "schema":"assetwright-native-before-after-forward-audit-v1",
        "study_id":STUDY,
        "status":"forward_reconstruction_pass" if all(checks.values()) else "forward_reconstruction_not_validated",
        "fresh_original_target_glbs":len(records),
        "real_student_generated_glbs":len(records)*len(VARIANTS),
        "native_unmodified_family_baselines":len(FAMILIES["validation"]),
        "source":"Only original AssetWright-AdvancedFormLab indexed Kotlin GLBs",
        "source_hashes_sha256":hashlib.sha256(
            "\n".join(sorted(all_target_hashes)).encode()).hexdigest(),
        "all_native_glbs_structurally_audited":True,
        "constant_unchanged_native_mean_vertex_rmse":nochange,
        "paired_teacher_free":paired,
        "paired_with_DINO":guided,
        "improvement_over_unchanged_native_fraction":improvement_over_nochange,
        "DINO_improvement_over_paired_without_teacher_fraction":improvement_vs_paired,
        "checks":checks,"per_operation":per_operation,
        "android_deployed":False,
        "external_AI_used_to_generate_meshes":False,
        "human_visual_review_complete":False,
        "cases":records
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--reconstructed",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    report=forward(a.source,a.reconstructed)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},indent=2))


if __name__=="__main__":
    main()

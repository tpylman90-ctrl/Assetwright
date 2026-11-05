"""4-way real ORIGINAL Kotlin native GLB forward audit on NEW heldout shapes.

No proxy metric, teacher embedding or labeled validation operation enters
the forward student predictions. Actual independent 3D indexed sources,
topology and normalized vertex distances decide research eligibility.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from dino_delta_school import STUDY,FAMILIES,expected_changes,read_case
from dino_native_forward_audit import audited,distance
from native_geometry_aware_student import VARIANTS

SCHEMA="assetwright-geometry-aware-fourway-native-forward-v5"
META="assetwright-native-before-after-reconstruction-v1"


def forward(source:Path,reconstructed:Path):
    if STUDY!="geometry_aware_v5":
        raise ValueError("Using an inspected rather than new original study")
    cases={stem:tuple(data) for stem,data in expected_changes().items()
           if data[0]=="validation"}
    wanted={stem+"__"+variant for stem in cases for variant in VARIANTS}
    found={p.stem for p in reconstructed.glob("*.glb")}
    meta={p.stem for p in reconstructed.glob("*.json")}
    if len(cases)!=96 or wanted!=found or wanted!=meta:
        raise ValueError("Incorrect real 384 GLB 4-way comparison cohort")
    records=[]
    hashes=[]
    per_op=defaultdict(list)
    for stem,identity in sorted(cases.items()):
        split,family,truth_op,truth_strength,baseline_stem=identity
        reference=source/(stem+".glb")
        original=read_case(source,stem,identity[:4],baseline=False)
        base=read_case(source,baseline_stem,
                       (split,family,"BASELINE",0.),baseline=True)
        baseline=source/(baseline_stem+".glb")
        if (audited(reference)["model_sha256"]!=original["source_sha256"]
            or audited(baseline)["model_sha256"]!=base["source_sha256"]):
            raise ValueError("Reference original native topology lost")
        row={
            "case":stem,"family":family,
            "target_operation":truth_op,"target_strength":truth_strength,
            "reference_glb_sha256":original["source_sha256"],
            "baseline_glb_sha256":base["source_sha256"],
            "unchanged_native_normalized_vertex_rmse":distance(reference,baseline)
        }
        hashes.append(original["source_sha256"])
        for variant in VARIANTS:
            guess=reconstructed/(stem+"__"+variant+".glb")
            audit=audited(guess)
            extra=json.loads(guess.with_suffix(".json").read_text())
            if not (
                extra.get("schema")==META
                and extra.get("case")==stem
                and extra.get("variant")==variant
                and extra.get("source_engine")=="AssetWright-AdvancedFormLab"
                and extra.get("reference_glb_sha256")==original["source_sha256"]
                and extra.get("baseline_glb_sha256")==base["source_sha256"]
                and extra.get("generated_glb_sha256")==audit["model_sha256"]
                and extra.get("chosen_operation") in (
                    "SECTION_LOFT","TANGENT_SWEEP","SECTION_TWIST",
                    "SUPERELLIPSE_PROFILE","LOWER_RECESS","RIBBED_FAIRING")
                and type(extra.get("chosen_strength")) in (float,int)
                and 0<=extra["chosen_strength"]<=1
            ):
                raise ValueError("Student reconstructed GLB no longer matches source SHA")
            predicted_op=extra["chosen_operation"]
            predicted_strength=extra["chosen_strength"]
            row[variant]={
                "operation":predicted_op,
                "strength":predicted_strength,
                "correct":predicted_op==truth_op,
                "strength_error":abs(predicted_strength-truth_strength),
                "normalized_vertex_rmse":distance(reference,guess),
                "generated_glb_sha256":audit["model_sha256"],
                "triangles":audit["triangles"]
            }
        records.append(row)
        per_op[truth_op].append(row)
    def aggregate(variant):
        return {
            "operation_accuracy":sum(row[variant]["correct"]
                                      for row in records)/len(records),
            "strength_mae":sum(row[variant]["strength_error"]
                               for row in records)/len(records),
            "mean_normalized_vertex_rmse":sum(
                row[variant]["normalized_vertex_rmse"] for row in records)/len(records),
            "per_operation":{
                op:{
                    "count":len(items),
                    "correct":sum(row[variant]["correct"] for row in items),
                    "mean_native_vertex_rmse":sum(
                        row[variant]["normalized_vertex_rmse"]
                        for row in items)/len(items)
                } for op,items in per_op.items()
            }
        }
    audit={name:aggregate(name) for name in VARIANTS}
    old_rmse=audit["prior"]["mean_normalized_vertex_rmse"]
    nochange=sum(x["unchanged_native_normalized_vertex_rmse"]
                 for x in records)/len(records)
    if old_rmse<=0 or nochange<=0:
        raise ValueError("Degenerate nochange/native geometry metric")
    gains={
        name:{
            "vs_prior":(old_rmse-audit[name]["mean_normalized_vertex_rmse"])/old_rmse,
            "vs_unchanged":(nochange-audit[name]["mean_normalized_vertex_rmse"])/nochange
        } for name in VARIANTS if name!="prior"
    }
    return {
        "schema":SCHEMA,"study_id":STUDY,
        "actual_original_Kotlin_blind_GLBS":len(records),
        "real_original_Kotlin_reconstructed_GLBS":len(records)*len(VARIANTS),
        "source_family_count":len(FAMILIES["validation"]),
        "source_hashes_sha256":hashlib.sha256(
            "\n".join(sorted(hashes)).encode()).hexdigest(),
        "original_source":"AssetWright original AdvancedFormLab only",
        "source_topology_checked":True,
        "external_AI_meshes_used":False,
        "unchanged_reference_RMSE":nochange,
        "variants":audit,"geometry_gains":gains,
        "individual_original_GLBS":records,
        "human_visual_review_required":True,
        "android_deployed":False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("source","reconstructed","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    report=forward(a.source,a.reconstructed)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="individual_original_GLBS"},
                     indent=2))


if __name__=="__main__":
    main()

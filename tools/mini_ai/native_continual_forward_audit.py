"""Independent native geometry proof for two versions of ONE saved Mini AI.

Both the unchanged previous student and the continually trained student
rebuild 96 fresh never-inspected Kotlin GLBs with their OWN predictions.
Do not confuse visually better scoring with a better actual mesh.
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
RESULT="assetwright-original-continued-native-forward-audit-v4"
VARIANTS=("prior","continued")


def forward(source:Path,reconstructed:Path)->dict:
    if STUDY!="strength_continual_v4":
        raise ValueError("Not a new blind continuation geometry audit")
    targets={stem:expected for stem,expected in expected_changes().items()
             if expected[0]=="validation"}
    expected_generated={f"{case}__{variant}"
                        for case in targets for variant in VARIANTS}
    found={p.stem for p in reconstructed.glob("*.glb")}
    meta={p.stem for p in reconstructed.glob("*.json")}
    if (len(targets)!=96 or found!=expected_generated
        or meta!=expected_generated):
        raise ValueError("Missing/foreign original predicted Kotlin GLBs")
    verified=[];source_hashes=[];per_operator=defaultdict(list)
    for stem,identity in sorted(targets.items()):
        split,family,op,level,baseline_case=identity
        original=read_case(source,stem,identity[:4],baseline=False)
        base=read_case(source,baseline_case,
                       (split,family,"BASELINE",0.),baseline=True)
        original_file=source/(stem+".glb")
        unchanged_file=source/(baseline_case+".glb")
        if (audited(original_file)["model_sha256"]!=original["source_sha256"]
            or audited(unchanged_file)["model_sha256"]!=base["source_sha256"]):
            raise ValueError("Expected source GLB topology and digest changed")
        item={
            "case":stem,"family":family,
            "actual_operation":op,"actual_strength":level,
            "source_sha256":original["source_sha256"],
            "baseline_sha256":base["source_sha256"],
            "unchanged_vertex_rmse":distance(original_file,unchanged_file)
        }
        for variant in VARIANTS:
            file=reconstructed/(stem+"__"+variant+".glb")
            info=json.loads(file.with_suffix(".json").read_text())
            audit=audited(file)
            if not (
                info.get("schema")==SCHEMA
                and info.get("case")==stem and info.get("variant")==variant
                and info.get("source_engine")=="AssetWright-AdvancedFormLab"
                and info.get("reference_glb_sha256")==original["source_sha256"]
                and info.get("baseline_glb_sha256")==base["source_sha256"]
                and info.get("generated_glb_sha256")==audit["model_sha256"]
                and info.get("chosen_operation") in (
                    "SECTION_LOFT","TANGENT_SWEEP","SECTION_TWIST",
                    "SUPERELLIPSE_PROFILE","LOWER_RECESS","RIBBED_FAIRING")
                and type(info.get("chosen_strength")) in (int,float)
                and 0<=info["chosen_strength"]<=1
            ):
                raise ValueError("Original native student/source GLB mismatch")
            item[variant]={
                "operation":info["chosen_operation"],
                "strength":info["chosen_strength"],
                "correct_operation":info["chosen_operation"]==op,
                "strength_error":abs(info["chosen_strength"]-level),
                "vertex_rmse":distance(original_file,file),
                "triangles":audit["triangles"],
                "generated_sha256":audit["model_sha256"]
            }
        source_hashes.append(original["source_sha256"])
        verified.append(item)
        per_operator[op].append(item)
    def score(variant):
        return {
            "operation_accuracy":
                sum(x[variant]["correct_operation"] for x in verified)/len(verified),
            "strength_mae":
                sum(x[variant]["strength_error"] for x in verified)/len(verified),
            "normalized_vertex_rmse":
                sum(x[variant]["vertex_rmse"] for x in verified)/len(verified),
        }
    before=score("prior");after=score("continued")
    if before["normalized_vertex_rmse"]<=0:
        raise ValueError("Prior original student GLB prediction error invalid")
    unchanged=sum(x["unchanged_vertex_rmse"] for x in verified)/len(verified)
    geometry_gain=(before["normalized_vertex_rmse"]-
                   after["normalized_vertex_rmse"])/before["normalized_vertex_rmse"]
    return {
        "schema":RESULT,"study_id":STUDY,
        "source":"AssetWright AdvancedFormLab ONLY; all native GLBs tested",
        "fresh_original_geometry_count":len(verified),
        "reconstructed_original_geometry_count":len(verified)*2,
        "independent_family_count":len(FAMILIES["validation"]),
        "no_outside_3d":True,
        "all_GLBS_structurally_valid":True,
        "blinded_source_hashes_digest":hashlib.sha256(
            "\n".join(sorted(source_hashes)).encode()).hexdigest(),
        "unchanged_source_normalized_vertex_rmse":unchanged,
        "prior":before,"continued":after,
        "continued_geometry_gain_vs_frozen_parent_fraction":geometry_gain,
        "operator_breakdown":{
            name:{
                "examples":len(items),
                "prior_correct":sum(x["prior"]["correct_operation"] for x in items),
                "continued_correct":sum(x["continued"]["correct_operation"] for x in items),
                "prior_vertex_rmse":sum(x["prior"]["vertex_rmse"] for x in items)/len(items),
                "continued_vertex_rmse":sum(x["continued"]["vertex_rmse"] for x in items)/len(items)
            } for name,items in per_operator.items()
        },
        "android_deployed":False,
        "human_review_required":True,
        "cases":verified
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("source","reconstructed","out"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    result=forward(a.source,a.reconstructed)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="cases"},indent=2))


if __name__=="__main__":
    main()

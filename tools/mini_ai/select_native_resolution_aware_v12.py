"""Freeze v12 checkpoint selection from ORIGINAL DEVELOPMENT GLB geometry only.

No blind geometry audit is read. Three genuine neural training conditions are
ranked by independent native 3D Chamfer; a fixed no-regression constraint for
form/operator/strength avoids selecting degenerate geometry tricks. This stage
MUST precede the blind geometry audit step in the GitHub workflow.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from native_resolution_aware_v12 import SCHEMA,WEIGHT_SCHEMA,CONDITIONS,VARIANTS
from native_resolution_aware_forward_audit import SCHEMA as FORWARD


def select(report,audit,lineage):
    if (report.get("schema")!=SCHEMA or lineage.get("schema")!=WEIGHT_SCHEMA
        or audit.get("schema")!=FORWARD
        or audit.get("study_id")!="resolution_aware_v12"
        or audit.get("evaluated_split")!="development"
        or audit.get("source_blind_native_shapes")!=288
        or audit.get("real_student_generated_GLBS")!=1152
        or audit.get("input_resolution_verified_from_unmodified_GLBS") is not True
        or audit.get("all_source_and_reconstructed_meshes_valid") is not True
        or set(audit.get("results",{}))!=set(VARIANTS)
        or report.get("configured_optimizer_seconds")!=900
        or report.get("completed_sessions")!=3
        or report.get("source_baseline_topology_available_at_inference") is not True):
        raise ValueError("Original development geometry cannot select checkpoint")
    parent=audit["results"]["parent_v10"]
    candidates={}
    for name in VARIANTS[1:]:
        x=audit["results"][name]
        if any(not math.isfinite(x[k]) for k in
               ("form_accuracy","operation_accuracy","strength_mae",
                "mean_3d_surface_chamfer")):
            raise ValueError("Non-finite native physical development metric")
        acceptable=(
            x["form_accuracy"]>=parent["form_accuracy"]-.001
            and x["operation_accuracy"]>=parent["operation_accuracy"]-.015
            and x["strength_mae"]<=parent["strength_mae"]+.015
            and x["predicted_distinct_archetypes"]==8
            and x["predicted_unique_triangle_topologies"]>=2
            and x["generic_shell_output_count"]==0)
        candidates[name]={
            "allowed_by_old_skill_guard":acceptable,
            "physical_3D_chamfer":x["mean_3d_surface_chamfer"],
            "operation_accuracy":x["operation_accuracy"],
            "strength_mae":x["strength_mae"],
            "form_accuracy":x["form_accuracy"]
        }
    valid=[k for k in VARIANTS[1:]
           if candidates[k]["allowed_by_old_skill_guard"]]
    # No blind-test winner selection, and no post-hoc switching.
    selection_pool=valid if valid else VARIANTS[1:]
    chosen=min(selection_pool,
               key=lambda k:(candidates[k]["physical_3D_chamfer"],
                             candidates[k]["strength_mae"],k))
    return {
        "schema":"assetwright-v12-development-only-physical-GLB-selection",
        "selected":chosen,
        "source_split":"development",
        "development_original_source_sha256":audit["source_hashes_sha256"],
        "real_dev_GLBS":1152,
        "source_topology_matched":True,
        "candidate_metrics":candidates,
        "parent_physical_3D_chamfer":parent["mean_3d_surface_chamfer"],
        "physical_development_gain_vs_parent_fraction":(
            parent["mean_3d_surface_chamfer"]-
            candidates[chosen]["physical_3D_chamfer"])/
            parent["mean_3d_surface_chamfer"],
        "selected_without_blind_3D_audit":True,
        "no_Android_deployment":True
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("evaluation","development_geometry","lineage","out"):
        p.add_argument("--"+k.replace("_","-"),type=Path,required=True)
    a=p.parse_args()
    e=json.loads(a.evaluation.read_text())
    d=json.loads(a.development_geometry.read_text())
    l=json.loads(a.lineage.read_text())
    r=select(e,d,l)
    e["initial_proxy_development_selected"]=e["development_selected"]
    e["development_selected"]=r["selected"]
    e["development_selection_source"]=r["schema"]
    e["development_native_physical_3D_gain"]=r["physical_development_gain_vs_parent_fraction"]
    l["final_method_selected_by_new_development"]=r["selected"]
    l["model_chosen_on_real_development_Kotlin_GLBS"]=True
    a.evaluation.write_text(json.dumps(e,indent=2)+"\n")
    a.lineage.write_text(json.dumps(l,indent=2)+"\n")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps(r,indent=2))


if __name__=="__main__":
    main()

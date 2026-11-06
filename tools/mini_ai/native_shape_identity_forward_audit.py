"""Independent 3D surface audit of 8 truly different ORIGINAL native forms.

Compares all original Kotlin source GLBs against 768 Kotlin student GLBs
with potentially DIFFERENT tessellation. Index-aligned RMSE would be
invalid here. Deterministic bidirectional, normalized surface Chamfer
works across unequal vertex and triangle counts. Also checks shape
identity diversity, per-form accuracy, and fallback-to-generic collapse.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

from dino_delta_school import STUDY,FAMILIES,expected_changes,read_case
from dino_native_forward_audit import audited,positions
from native_shape_identity_student import FORMS,VARIANTS

SCHEMA="assetwright-original-threeview-identity-real-chamfer-v7"
META="assetwright-neural-multiform-source-reconstruction-v7"


def surface_points(file:Path):
    import numpy as np
    xyz,triangle_indices,_=positions(file)
    points=np.asarray(xyz,dtype=np.float32)
    faces=np.asarray(triangle_indices,dtype=np.int64).reshape(-1,3)
    if len(points)>2000 or len(faces)>3000 or len(faces)<900:
        raise ValueError("Excessive/degenerate owned multi-form topology")
    if not np.isfinite(points).all():
        raise ValueError("Original native GLB surface points are not finite")
    # Fixed ordering deterministic face centroids: comparable even with
    # varying original mesh topology and vertex indexing.
    subset=np.linspace(0,len(faces)-1,384,dtype=np.int64)
    sampled=(points[faces[subset,0]]+
             points[faces[subset,1]]+
             points[faces[subset,2]])/3.
    return sampled,points


def chamfer(reference:Path,proposal:Path)->float:
    import numpy as np
    from scipy.spatial import cKDTree
    a,source=surface_points(reference)
    b,_=surface_points(proposal)
    span=np.max(source,axis=0)-np.min(source,axis=0)
    scale=float(np.linalg.norm(span))
    if not .1<scale<100:
        raise ValueError("Degenerate original 3D source shape")
    da=cKDTree(b).query(a,k=1)[0]
    db=cKDTree(a).query(b,k=1)[0]
    error=float(np.sqrt((np.mean(da**2)+np.mean(db**2))/2)/scale)
    if not math.isfinite(error) or error<0 or error>5:
        raise ValueError("Invalid normalized 3D surface comparison")
    return error


def compare(source:Path,reconstruction:Path):
    if STUDY!="shape_identity_v7":
        raise ValueError("Fresh multi-shape source audit not selected")
    cases={stem:identity for stem,identity in expected_changes().items()
           if identity[0]=="validation"}
    wanted={stem+"__"+variant for stem in cases for variant in VARIANTS}
    glbs={p.stem for p in reconstruction.glob("*.glb")}
    files={p.stem for p in reconstruction.glob("*.json")}
    if (len(cases)!=384 or wanted!=glbs or files!=glbs):
        raise ValueError("Missing/foreign 768 original Kotlin student GLBs")
    individual=[]
    digests=[]
    archetype_groups=defaultdict(list)
    for stem,identity in sorted(cases.items()):
        split,family,original_op,original_strength,baseline_stem=identity
        target=source/(stem+".glb")
        baseline=source/(baseline_stem+".glb")
        known=read_case(source,stem,identity[:4],baseline=False)
        original_form=known["meta"]["archetype"]
        previous=read_case(source,baseline_stem,
            (split,family,"BASELINE",0.),baseline=True)
        if (audited(target)["model_sha256"]!=known["source_sha256"]
            or audited(baseline)["model_sha256"]!=previous["source_sha256"]):
            raise ValueError("Original source or baseline changes after rendering")
        row={
            "case":stem,"family":family,"target_form":original_form,
            "target_operation":original_op,"target_strength":original_strength,
            "original_glb_sha256":known["source_sha256"],
            "original_mesh_triangles":known["audit"]["triangles"],
            "unchanged_native_chamfer":chamfer(target,baseline)
        }
        digests.append(known["source_sha256"])
        for variant in VARIANTS:
            file=reconstruction/(stem+"__"+variant+".glb")
            meta=json.loads(file.with_suffix(".json").read_text())
            audit=audited(file)
            if not (
                meta.get("schema")==META
                and meta.get("case")==stem
                and meta.get("variant")==variant
                and meta.get("source_engine")=="AssetWright-NativeDiverseFormLab"
                and meta.get("reference_glb_sha256")==known["source_sha256"]
                and meta.get("baseline_glb_sha256")==previous["source_sha256"]
                and meta.get("generated_glb_sha256")==audit["model_sha256"]
                and meta.get("predicted_archetype") in FORMS
                and meta.get("predicted_operation") in (
                    "SECTION_LOFT","TANGENT_SWEEP","SECTION_TWIST",
                    "SUPERELLIPSE_PROFILE","LOWER_RECESS","RIBBED_FAIRING")
                and type(meta.get("predicted_strength")) in (int,float)
                and 0<=meta["predicted_strength"]<=1
                and meta.get("triangles")==audit["triangles"]
            ):
                raise ValueError("Student form/operation did not generate a valid real native GLB")
            row[variant]={
                "form":meta["predicted_archetype"],
                "operation":meta["predicted_operation"],
                "strength":meta["predicted_strength"],
                "form_correct":meta["predicted_archetype"]==original_form,
                "operation_correct":meta["predicted_operation"]==original_op,
                "strength_error":abs(meta["predicted_strength"]-original_strength),
                "surface_chamfer":chamfer(target,file),
                "triangles":audit["triangles"],
                "native_glb_sha256":audit["model_sha256"]
            }
        individual.append(row)
        archetype_groups[original_form].append(row)
    def metrics(variant):
        predicted_form={r[variant]["form"] for r in individual
                        if r[variant]["form"]!="LEGACY_SHELL"}
        seen_topologies={r[variant]["triangles"] for r in individual}
        return {
            "form_accuracy":sum(r[variant]["form_correct"] for r in individual)/len(individual),
            "operation_accuracy":sum(r[variant]["operation_correct"] for r in individual)/len(individual),
            "strength_mae":sum(r[variant]["strength_error"] for r in individual)/len(individual),
            "mean_3d_surface_chamfer":sum(
                r[variant]["surface_chamfer"] for r in individual)/len(individual),
            "predicted_distinct_archetypes":len(predicted_form),
            "predicted_unique_triangle_topologies":len(seen_topologies),
            "generic_shell_output_count":sum(r[variant]["form"]=="LEGACY_SHELL"
                                              for r in individual),
            "per_form":{
                name:{
                    "count":len(items),
                    "correct_form":sum(row[variant]["form_correct"] for row in items),
                    "operation_correct":sum(row[variant]["operation_correct"] for row in items),
                    "surface_chamfer":sum(
                        row[variant]["surface_chamfer"] for row in items)/len(items)
                } for name,items in archetype_groups.items()
            },
            "twist_operation_chamfer":sum(
                r[variant]["surface_chamfer"] for r in individual
                if r["target_operation"]=="SECTION_TWIST")/64
        }
    scored={variant:metrics(variant) for variant in VARIANTS}
    parent=scored["prior"]["mean_3d_surface_chamfer"]
    nochange=sum(r["unchanged_native_chamfer"] for r in individual)/len(individual)
    if parent<=0 or nochange<=0:
        raise ValueError("Original native shape diversity has degenerate reference distances")
    return {
        "schema":SCHEMA,"study_id":"shape_identity_v7",
        "original_source_chosen_by":"original Kotlin NativeDiverseFormLab",
        "reconstruction_form_chosen_by":"actual student neural form head, never target form",
        "source_blind_native_shapes":len(individual),
        "real_student_generated_GLBS":len(individual)*len(VARIANTS),
        "original_validation_families":len(FAMILIES["validation"]),
        "original_validation_archetypes":len(archetype_groups),
        "original_validation_topologies":len({
            x["original_mesh_triangles"] for x in individual}),
        "all_source_and_reconstructed_meshes_valid":True,
        "source_hashes_sha256":hashlib.sha256(
            "\n".join(sorted(digests)).encode()).hexdigest(),
        "external_meshes_used":False,
        "unchanged_native_surface_chamfer":nochange,
        "results":scored,
        "physical_3d_gain_vs_generic_parent":{
            variant:(parent-scored[variant]["mean_3d_surface_chamfer"])/parent
            for variant in VARIANTS if variant!="prior"},
        "individual_GLBS":individual,
        "human_review_required":True,
        "android_deployed":False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("source","reconstructed","out"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    result=compare(a.source,a.reconstructed)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="individual_GLBS"},
                     indent=2))


if __name__=="__main__":
    main()

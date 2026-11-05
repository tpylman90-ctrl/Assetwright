"""Independent forward GLB/topology proof of the student's native branch site.

Corresponding-vertex comparisons only within source-generated fixed-topology
model family. This is NOT proof of collision-free CSG, true CAD G2 seams, or
choice of a useful boss location from natural-language instructions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from generated_glb_critic import _read_glb,_accessor,inspect
from native_branch_student import morphology,V,F

def positions(path:Path):
    doc,blob,_=_read_glb(path)
    prim=doc["meshes"][0]["primitives"][0]
    return np.asarray(_accessor(doc,blob,prim["attributes"]["POSITION"],
                               "positions"),dtype=np.float64)

def run(source:Path,reconstructed:Path,out:Path):
    files=sorted(reconstructed.glob("*.glb"))
    if len(files)!=160 or len({x.stem for x in files})!=160:
        raise ValueError("Incomplete or duplicated 160 geometry re-creations")
    evidence=[]
    for file in files:
        stem=file.stem
        phase=stem.split("__")[0]
        if phase not in ("validation","aspect_shift"):
            raise ValueError("Unexpected source-training family in forward audit")
        target=source/(stem+".glb")
        metadata=json.loads((source/(stem+".json")).read_text())
        source_hash=hashlib.sha256(target.read_bytes()).hexdigest()
        rebuilt_hash=hashlib.sha256(file.read_bytes()).hexdigest()
        if (source_hash!=metadata["source_glb_sha256"] or
                rebuilt_hash!=file.with_suffix(".sha256").read_text().strip()):
            raise ValueError("Source or Kotlin-model-generated geometry hash failed")
        report=inspect(file)
        if not(
            report["model_sha256"]==rebuilt_hash and
            report["mesh_parts"]==1 and report["triangles"]==F and
            report["boundary_edges"]==0 and
            report["nonmanifold_edges"]==0 and
            report["invalid_triangles"]==0 and
            report["inverted_closed_parts"]==0 and
            report["parts"][0]["signed_volume"]>0):
            raise ValueError("Student-created native branch failed mesh structure")
        measured,physics=morphology(file)
        if (physics["topology"]["genus"]!=1 or
            not physics["topology"]["welded_branch"]):
            raise ValueError("Actual branch connection not present in student GLB")
        a=positions(target)
        b=positions(file)
        if a.shape!=b.shape or a.shape!=(V,3):
            raise ValueError("Native source does not share expected vertex lattice")
        dims=np.array((metadata["width"],metadata["height"],
                       metadata["length"]),dtype=np.float64)
        error=np.linalg.norm((a-b)/dims,axis=1)
        rms=float(np.sqrt(np.mean(error*error)))
        evidence.append({
            "source":stem,"phase":phase,
            "original_source_sha256":source_hash,
            "student_reconstruction_sha256":rebuilt_hash,
            "normalized_surface_rms":rms,
            "p95_normalized_distance":float(np.quantile(error,.95)),
            "connected_through_bore_and_blind_socket":True
        })
    summary={}
    for phase in ("validation","aspect_shift"):
        cases=[r for r in evidence if r["phase"]==phase]
        if len(cases)!=80:
            raise ValueError("Expected 80 source-disjoint student reconstructions")
        summary[phase]={
            "sources":80,
            "mean_surface_rms":sum(x["normalized_surface_rms"]
                                   for x in cases)/len(cases),
            "worst_surface_rms":max(x["normalized_surface_rms"] for x in cases),
            "mean_p95_distance":sum(x["p95_normalized_distance"]
                                    for x in cases)/len(cases)
        }
    checks={
        "160_source_sha256_and_genus_one_integrity_verified":True,
        "dimension_mean_surface_rms":summary["validation"]["mean_surface_rms"]<=.018,
        "aspect_mean_surface_rms":summary["aspect_shift"]["mean_surface_rms"]<=.028,
        "dimension_worst_surface_rms":summary["validation"]["worst_surface_rms"]<=.08,
        "aspect_worst_surface_rms":summary["aspect_shift"]["worst_surface_rms"]<=.11
    }
    result={
        "schema":"assetwright-native-branch-forward-audit-v1",
        "status":"passed_development_only" if all(checks.values()) else "rejected",
        "source_comparison":"original Kotlin native hull target vs student-driven Kotlin reconstruction",
        "groups":summary,"checks":checks,"cases":evidence,
        "passed":all(checks.values()),"actual_source_geometry_used":True,
        "human_approved":False,"android_deployed":False,
        "limitations":"Known topology, source-vertex correspondence; no semantic design or general-purpose mesh Boolean."
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"groups":summary,"checks":checks},indent=2))
    if not result["passed"]:
        raise SystemExit("Native branching geometry forward validation REJECTED")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--reconstructed",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    run(a.source,a.reconstructed,a.out)

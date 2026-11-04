"""Independent forward-surface proof: target-vs-student original Kotlin GLBs."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from generated_glb_critic import _read_glb,_accessor,inspect

SCHEMA="assetwright-composed-reconstruction-audit-v1"

def points(path:Path)->np.ndarray:
    doc,blob,_=_read_glb(path)
    assert len(doc["meshes"])==1
    primitive=doc["meshes"][0]["primitives"][0]
    return np.asarray(_accessor(doc,blob,primitive["attributes"]["POSITION"],
                                "positions"),dtype=np.float64)


def evaluate(source:Path,recon:Path,out:Path)->dict:
    stems=[p.stem for p in sorted(recon.glob("*.glb"))]
    if len(stems)!=320 or len(set(stems))!=320:
        raise ValueError("Incomplete independently generated 320 predictions")
    result={"schema":SCHEMA,"status":"development_only",
            "groups":{},"predictions":[],
            "tests":{},"model_generated_final_geometry":True,
            "generator":"original AssetWright Kotlin NativeCompositionLab",
            "note":"Corresponding-vertex error on source-generated hulls; not novel external CAD designs"}
    for stem in stems:
        phase=stem.split("__")[0]
        if phase not in ("validation","aspect_shift"):
            raise ValueError("Training-source leakage into reconstructed audit")
        target=source/(stem+".glb")
        targetmeta=json.loads((source/(stem+".json")).read_text())
        generated=recon/(stem+".glb")
        reconstructed_hash=hashlib.sha256(generated.read_bytes()).hexdigest()
        source_hash=hashlib.sha256(target.read_bytes()).hexdigest()
        if targetmeta["source_glb_sha256"]!=source_hash:
            raise ValueError("Invalid original shape target provenance")
        if reconstructed_hash!=(recon/(stem+".sha256")).read_text().strip():
            raise ValueError("Original reconstructed GLB SHA-256 mismatch")
        audit=inspect(generated)
        if (audit["model_sha256"]!=reconstructed_hash
            or audit["mesh_parts"]!=1 or audit["triangles"]!=2112
            or audit["invalid_triangles"]!=0
            or audit["boundary_edges"]!=0
            or audit["nonmanifold_edges"]!=0
            or audit["inverted_closed_parts"]!=0
            or audit["parts"][0]["signed_volume"]<=0):
            raise ValueError("Reconstructed native mesh failed independent topology check")
        a,b=points(target),points(generated)
        if a.shape!=b.shape or a.shape!=(1058,3):
            raise ValueError("Mismatched true corresponding native vertex lattice")
        dims=np.array([targetmeta["width"],targetmeta["height"],
                       targetmeta["length"]])
        differences=np.linalg.norm((a-b)/dims,axis=1)
        mean=float(np.sqrt(np.mean(differences**2)))
        p95=float(np.quantile(differences,.95))
        result["predictions"].append({
            "case":stem,"phase":phase,"source_glb_sha256":source_hash,
            "reconstructed_glb_sha256":reconstructed_hash,
            "normalized_surface_rms":mean,"p95_surface_distance":p95})
    for phase in ("validation","aspect_shift"):
        chosen=[x for x in result["predictions"] if x["phase"]==phase]
        if len(chosen)!=160:
            raise ValueError("Uneven reconstructed generalization split")
        result["groups"][phase]={
            "count":len(chosen),
            "mean_normalized_surface_rms":sum(x["normalized_surface_rms"]
                                              for x in chosen)/len(chosen),
            "mean_p95_surface_distance":sum(x["p95_surface_distance"]
                                            for x in chosen)/len(chosen),
            "worst_normalized_surface_rms":max(x["normalized_surface_rms"]
                                               for x in chosen)
        }
    result["tests"]={
        "all_320_reconstructed_source_hashes_and_topology_pass":True,
        "heldout_forward_rms":result["groups"]["validation"][
            "mean_normalized_surface_rms"]<=.028,
        "aspect_forward_rms":result["groups"]["aspect_shift"][
            "mean_normalized_surface_rms"]<=.038,
        "heldout_worst_case_rms":result["groups"]["validation"][
            "worst_normalized_surface_rms"]<=.11,
        "aspect_worst_case_rms":result["groups"]["aspect_shift"][
            "worst_normalized_surface_rms"]<=.14
    }
    result["passed"]=all(result["tests"].values())
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"groups":result["groups"],"tests":result["tests"]},
                     indent=2))
    if not result["passed"]:
        raise SystemExit("Owned forward modeling reconstruction did not pass")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--reconstructed",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    evaluate(a.source,a.reconstructed,a.out)

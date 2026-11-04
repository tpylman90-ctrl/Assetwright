"""Independent original/native GLB forward reconstruction and topology audit."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from generated_glb_critic import _read_glb, _accessor, inspect
from native_interface_student import morphology

def positions(path):
    doc,blob,_=_read_glb(path)
    if len(doc.get("meshes",[]))!=1:
        raise ValueError("Missing one-shell reconstructed geometry")
    prim=doc["meshes"][0]["primitives"][0]
    return np.asarray(_accessor(doc,blob,prim["attributes"]["POSITION"],
                                "positions"),dtype=np.float64)

def run(source:Path,reconstruction:Path,out:Path):
    files=sorted(reconstruction.glob("*.glb"))
    if len(files)!=120 or len({p.stem for p in files})!=120:
        raise ValueError("Wrong number of independently reconstructed shapes")
    evidence=[]
    for path in files:
        stem=path.stem
        phase=stem.split("__")[0]
        if phase not in ("validation","aspect_shift"):
            raise ValueError("Training source appeared in forward reconstruction")
        source_path=source/(stem+".glb")
        metadata=json.loads((source/(stem+".json")).read_text())
        source_sha=hashlib.sha256(source_path.read_bytes()).hexdigest()
        predicted_sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if (source_sha!=metadata["source_glb_sha256"] or
            predicted_sha!=path.with_suffix(".sha256").read_text().strip()):
            raise ValueError("Source or predicted GLB SHA mismatch")
        report=inspect(path)
        if not (report["mesh_parts"]==1 and report["triangles"]==5248
                and report["invalid_triangles"]==0
                and report["boundary_edges"]==0
                and report["nonmanifold_edges"]==0
                and report["inverted_closed_parts"]==0
                and report["parts"][0]["signed_volume"]>0):
            raise ValueError("Reconstruction not a closed outward source mesh")
        signals,physical=morphology(path)
        if physical["topology"]["genus"]!=1:
            raise ValueError("Reconstructed tunnel is not topologically real")
        original=positions(source_path)
        rebuilt=positions(path)
        if original.shape!=rebuilt.shape or original.shape!=(2624,3):
            raise ValueError("No homologous original native correspondence")
        scale=np.array((metadata["width"],metadata["height"],
                        metadata["length"]),dtype=np.float64)
        error=np.linalg.norm((original-rebuilt)/scale,axis=1)
        evidence.append({"stem":stem,"phase":phase,
            "target_sha256":source_sha,"student_sha256":predicted_sha,
            "normalized_surface_rms":float(np.sqrt(np.mean(error**2))),
            "p95_normalized_surface_distance":float(np.quantile(error,.95)),
            "true_through_bore":True,"one_connected_shell":True})
    groups={}
    for phase in ("validation","aspect_shift"):
        a=[r for r in evidence if r["phase"]==phase]
        if len(a)!=60:
            raise ValueError("Invalid blind-family reconstruction split")
        groups[phase]={
            "source_glbs":len(a),
            "mean_normalized_surface_rms":sum(r["normalized_surface_rms"]
                                              for r in a)/len(a),
            "worst_normalized_surface_rms":max(r["normalized_surface_rms"]
                                               for r in a),
            "mean_p95_distance":sum(r["p95_normalized_surface_distance"]
                                    for r in a)/len(a)}
    checks={
        "all_120_independent_source_sha_and_manifold_topology":True,
        "new_dimension_forward_rms":groups["validation"][
            "mean_normalized_surface_rms"]<=.012,
        "aspect_shift_forward_rms":groups["aspect_shift"][
            "mean_normalized_surface_rms"]<=.016,
        "new_dimension_worst_surface_rms":groups["validation"][
            "worst_normalized_surface_rms"]<=.026,
        "aspect_worst_surface_rms":groups["aspect_shift"][
            "worst_normalized_surface_rms"]<=.033
    }
    result={
        "schema":"assetwright-native-through-bore-forward-audit-v1",
        "status":"verified_development_only" if all(checks.values()) else "rejected",
        "groups":groups,"checks":checks,"passed":all(checks.values()),
        "evidence":evidence,
        "limitations":"Same source parametric housing family; measured source-vertex correspondence, not novel object design, Boolean flexibility or human visual approval."
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"groups":groups,"checks":checks},indent=2))
    if not result["passed"]:
        raise SystemExit("Native interface model failed forward surface reconstruction")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--reconstructed",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    run(a.source,a.reconstructed,a.out)

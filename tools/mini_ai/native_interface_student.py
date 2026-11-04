"""Learn connected through-bore / blended-flange dimensions from original GLBs.

Own source-only ridge student, no pretrained geometry, no metadata features,
no image-to-3D service. Audit a genuine genus-one connected shell separately
from learning numeric parameter strengths. Controlled synthetic research only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from generated_glb_critic import _read_glb, _accessor, inspect

SCHEMA = "assetwright-native-interface-v1"
STUDENT = "assetwright-owned-native-interface-inverse-v1"
PHASES = {
    "train": (12,30),
    "validation": (4,15),
    "aspect_shift": (4,15),
}
STRENGTHS = ("bore_strength","flange_strength","blend_strength")
N,M=32,40
V=(M+1)*N*2
F=M*N*4+N*4
E=3*F//2
SAMPLES=480

def expected_stems():
    return {
        f"{phase}__if{family:02d}__s{index:02d}"
        for phase,(families,cases) in PHASES.items()
        for family in (range(1,families+1) if phase=="train"
                       else range(5,5+families))
        for index in range(cases)
    }

def expected_recipe(phase,family,index):
    # The native Kotlin source recipe uses the externally visible
    # one-based family NUMBER; the first audit incorrectly subtracted one.
    # Keep the signed physical source labels intact and fix the auditor,
    # never the acceptance limits.
    i=family
    if phase=="train":
        return np.array([.12+((index*k+i*11)%79)/100.
                         for k in (19,31,47)])
    if phase=="validation":
        return np.array([.125+((index*k+i*13)%77)/100.
                         for k in (19,31,47)])
    return np.array([.137+((index*k+i*17)%75)/100.
                     for k in (19,31,47)])

def connected_topology(vertices, indices):
    if len(vertices)!=V or len(indices)!=F*3:
        raise ValueError("Wrong original indexed through-bore lattice")
    edges=defaultdict(list)
    graph=defaultdict(set)
    for a,b,c in np.asarray(indices).reshape((-1,3)):
        a,b,c=map(int,(a,b,c))
        if len({a,b,c})!=3:
            raise ValueError("Degenerate indexed triangle")
        for start,end in ((a,b),(b,c),(c,a)):
            if not (0<=start<V and 0<=end<V):
                raise ValueError("Out-of-bounds indexed shell")
            edges[tuple(sorted((start,end)))].append((start,end))
            graph[start].add(end)
            graph[end].add(start)
    if len(edges)!=E or any(len(owners)!=2 or owners[0]==owners[1]
                          for owners in edges.values()):
        raise ValueError("Open, duplicated or inconsistently oriented edges")
    visited={0}
    queue=deque([0])
    while queue:
        for neighbor in graph[queue.popleft()]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    if len(visited)!=V:
        raise ValueError("Disconnected shell or isolated geometry")
    euler=V-len(edges)+F
    if euler!=0:
        raise ValueError("No topological genus-one through-bore")
    return {"vertices":V,"faces":F,"edges":E,
            "components":1,"euler_characteristic":euler,
            "genus":1,"all_directed_edges_opposed":True}

def morphology(path:Path):
    doc,blob,_=_read_glb(path)
    if len(doc.get("meshes",[]))!=1 or len(doc["meshes"][0]["primitives"])!=1:
        raise ValueError("Expected one original solid hull")
    prim=doc["meshes"][0]["primitives"][0]
    pts=np.asarray(_accessor(doc,blob,prim["attributes"]["POSITION"],
                             "positions"),dtype=np.float64)
    indices=np.asarray(_accessor(doc,blob,prim["indices"],"indices"),
                       dtype=np.int64)
    topo=connected_topology(pts,indices)
    outer=pts[:(M+1)*N].reshape(M+1,N,3)
    inner=pts[(M+1)*N:].reshape(M+1,N,3)
    # glTF is X-right,Y-up,Z-longitudinal. Read native morphology only.
    width_base=float(outer[0,0,0])
    height_base=float(outer[0,8,1])
    if width_base<=.15 or height_base<=.15:
        raise ValueError("Invalid physical base section")
    bore_ratio=float(inner[0,0,0]/width_base)
    profile=outer[:,0,0]/width_base
    height_profile=outer[:,8,1]/height_base
    if np.max(np.abs(profile-height_profile))>1.e-5:
        raise ValueError("Flange exterior is not a coherent loft")
    if np.max(np.abs(inner[:,0,0]/width_base-bore_ratio))>1.e-5:
        raise ValueError("Invalid through-bore wall alignment")
    amp=float(profile[24]-1)
    if not (.075<amp<.46 and .125<bore_ratio<.50):
        raise ValueError("Incorrect hollow interface physical dimensions")
    if abs(profile[0]-1)>1e-6 or abs(profile[-1]-1)>1e-6:
        raise ValueError("Flange is disconnected from base profile")
    slope_jump=float(np.max(np.abs(np.diff(profile,n=2))))
    if slope_jump>.063:
        raise ValueError("Flange transition exceeds discrete smoothness budget")
    max_first=float(np.max(np.abs(np.diff(profile))))
    if max_first>.118:
        raise ValueError("Excessively abrupt flange shoulder")
    # A source-measured normalized bump integral gives the actual relative
    # transition width. No control name, strength or recipe enters X.
    area=float(np.trapezoid(profile-1,dx=1/M)/amp)
    features=np.array([bore_ratio,amp,area,slope_jump],dtype=np.float64)
    if not np.all(np.isfinite(features)):
        raise ValueError("Nonfinite independently measured geometry")
    return features, {
        "topology":topo,"inner_half_width":float(inner[0,0,0]),
        "outer_half_width":width_base,
        "bore_ratio":bore_ratio,"flange_amplitude":amp,
        "normalized_transition_area":area,
        "max_second_difference":slope_jump,
        "max_first_difference":max_first
    }

def load(source:Path):
    expected=expected_stems()
    if len(expected)!=SAMPLES:
        raise ValueError("Incorrect original curriculum size")
    raw={path.stem for path in source.glob("*.glb")}
    manifests={path.stem for path in source.glob("*.json")}
    if raw!=expected or manifests!=expected:
        raise ValueError("Incomplete or unexpected original geometry data")
    rows=[]
    hashes=set()
    for stem in sorted(expected):
        match=re.fullmatch(r"(train|validation|aspect_shift)__if(\d\d)__s(\d\d)",stem)
        if not match:
            raise ValueError("Malformed source identity")
        phase,fam_s,idx_s=match.groups()
        family,index=int(fam_s),int(idx_s)
        families=(range(1,13) if phase=="train" else range(5,9))
        if not(family in families and 0<=index<PHASES[phase][1]):
            raise ValueError("Wrong original interface study partition")
        file=source/(stem+".glb")
        metadata=json.loads((source/(stem+".json")).read_text())
        sha=hashlib.sha256(file.read_bytes()).hexdigest()
        targets=np.asarray([metadata.get(key) for key in STRENGTHS],dtype=np.float64)
        expected_controls=expected_recipe(phase,family,index)
        if not (
            metadata.get("schema")==SCHEMA and metadata.get("phase")==phase
            and metadata.get("family")==family and metadata.get("case")==stem
            and metadata.get("generator")=="AssetWright-NativeInterfaceLab"
            and metadata.get("source_glb_sha256")==sha
            and metadata.get("segments")==N and metadata.get("stations")==M
            and np.all(np.isfinite(targets))
            and np.max(np.abs(targets-expected_controls))<2e-5
            and all(type(metadata.get(k)) in (float,int)
                    and math.isfinite(metadata[k]) and metadata[k]>0
                    for k in ("length","width","height"))
        ):
            raise ValueError("Untrusted source/provenance/strength labels")
        if sha in hashes:
            raise ValueError("Duplicate original GLB source hashes")
        hashes.add(sha)
        audit=inspect(file)
        if not (
            audit["mesh_parts"]==1 and audit["triangles"]==F
            and audit["boundary_edges"]==0 and audit["nonmanifold_edges"]==0
            and audit["invalid_triangles"]==0
            and audit["inverted_closed_parts"]==0
            and audit["parts"][0]["signed_volume"]>0
        ):
            raise ValueError("Independent manifold/volume auditor rejected source")
        x,physics=morphology(file)
        rows.append({
            "phase":phase,"stem":stem,"sha":sha,
            "features":x,"strengths":targets,
            "dimensions":(metadata["length"],metadata["width"],metadata["height"]),
            "measured":physics
        })
    return rows

def fit(rows):
    if len(rows)!=360 or any(row["phase"]!="train" for row in rows):
        raise ValueError("Training only accepts 360 original fresh native GLBs")
    X=np.stack([row["features"] for row in rows])
    Y=np.stack([row["strengths"] for row in rows])
    mean=X.mean(axis=0)
    std=np.maximum(X.std(axis=0),.01)
    A=np.column_stack((np.ones(len(rows)),(X-mean)/std))
    reg=np.diag([0.,.002,.002,.002,.002])
    weights=np.linalg.solve(A.T@A+reg,A.T@Y)
    return {
        "schema":STUDENT,
        "architecture":"self-trained multi-target ridge response student",
        "source_glbs":len(rows),"feature_mean":mean.tolist(),
        "feature_std":std.tolist(),"weights":weights.tolist(),
        "features":["source_bore_ratio","source_flange_amplitude",
                    "normalized_flange_transition_area",
                    "local_discrete_surface_curvature"],
        "targets":list(STRENGTHS),
        "training_hashes_sha256":hashlib.sha256(
            "\n".join(sorted(row["sha"] for row in rows)).encode()).hexdigest(),
        "external_mesh_generator":False,"android_deployable":False
    }

def infer(model,X):
    raw=np.atleast_2d(X)
    std=np.array(model["feature_std"])
    mean=np.array(model["feature_mean"])
    matrix=np.column_stack((np.ones(len(raw)),(raw-mean)/std))
    return np.clip(matrix@np.array(model["weights"]),0,1)

def score(model,rows,phase):
    if not rows or any(row["phase"]!=phase for row in rows):
        raise ValueError("Evaluation family mixing")
    actual=np.stack([r["strengths"] for r in rows])
    guess=infer(model,np.stack([r["features"] for r in rows]))
    diff=np.abs(actual-guess)
    summary={
        "source_glbs":len(rows),
        "mean_parameter_mae":float(diff.mean()),
        "max_parameter_error":float(diff.max()),
        "per_control_mae":{name:float(diff[:,i].mean())
                           for i,name in enumerate(STRENGTHS)},
        "constant_point_five_baseline_mae":float(np.abs(actual-.5).mean())
    }
    cases=[{
        "stem":row["stem"],"source_sha256":row["sha"],
        "target":row["strengths"].tolist(),"predicted":pred.tolist(),
        "per_control_absolute_error":err.tolist()
    } for row,pred,err in zip(rows,guess,diff)]
    return summary,cases

def acceptance(ordinary,extreme):
    return {
        "heldout_control_mae":ordinary["mean_parameter_mae"]<=.018,
        "aspect_control_mae":extreme["mean_parameter_mae"]<=.027,
        "heldout_each_strength":all(x<=.024 for x in ordinary["per_control_mae"].values()),
        "aspect_each_strength":all(x<=.036 for x in extreme["per_control_mae"].values()),
        "heldout_beats_constant_by_point_thirteen":
            ordinary["constant_point_five_baseline_mae"]-
            ordinary["mean_parameter_mae"]>=.13,
        "aspect_beats_constant_by_point_thirteen":
            extreme["constant_point_five_baseline_mae"]-
            extreme["mean_parameter_mae"]>=.13,
        "heldout_max_error_bound":ordinary["max_parameter_error"]<=.07,
        "aspect_max_error_bound":extreme["max_parameter_error"]<=.09,
    }

def run(source:Path,out:Path):
    rows=load(source)
    train=[r for r in rows if r["phase"]=="train"]
    validation=[r for r in rows if r["phase"]=="validation"]
    shifted=[r for r in rows if r["phase"]=="aspect_shift"]
    if tuple(map(len,(train,validation,shifted)))!=(360,60,60):
        raise ValueError("Original training/evaluation split imbalance")
    model=fit(train)
    score_v,cases_v=score(model,validation,"validation")
    score_s,cases_s=score(model,shifted,"aspect_shift")
    gates=acceptance(score_v,score_s)
    report={
        "schema":"assetwright-connected-interface-study-v1",
        "status":"passed_development_only" if all(gates.values()) else "rejected_development_candidate",
        "owned_source_glbs":480,"train_source_glbs":360,
        "dimension_holdout_glbs":60,"aspect_holdout_glbs":60,
        "topology":"one connected closed genus-one through-bore with annular stitched ends",
        "per_glb_triangle_count":F,
        "source_hashes_unique":True,"physical_topology_audits":480,
        "dimension_holdout":score_v,"aspect_holdout":score_s,
        "checks":gates,"prior_checkpoints_unchanged":True,
        "android_deployed":False,"human_visual_approval":False,
        "limitations":"Single original parametric housing family, not arbitrary Boolean modeling or welded separate bodies; analytic C2 flange envelope is only approximated by triangles; no true Class-A NURBS/G2 face boundary."
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"interface_report.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"candidate_interface_student.json").write_text(json.dumps(model,indent=2)+"\n")
    (out/"heldout_predictions.json").write_text(json.dumps(
        {"validation":cases_v,"aspect_shift":cases_s},indent=2)+"\n")
    with (out/"predicted_native_controls.tsv").open("w") as stream:
        for row,case in zip([*validation,*shifted],[*cases_v,*cases_s]):
            assert row["stem"]==case["stem"]
            stream.write("\t".join((
                row["stem"],
                ",".join(f"{v:.9f}" for v in case["predicted"]),
                ",".join(str(v) for v in row["dimensions"])))+"\n")
    print(json.dumps({"status":report["status"],
        "ordinary":score_v,"aspect":score_s,"gates":gates},indent=2))
    if not all(gates.values()):
        raise SystemExit("Native interface student rejected under frozen gates")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.source,a.out)

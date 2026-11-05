"""Original native side-branch placement and blind-socket inverse learner.

520 original Kotlin GLBs: 360 training / 80 new dimensions / 80 extreme
proportions. Independently verifies source provenance, connected genus-one
topology, branch ring geometry and geometry-only learning features.

This student learns WHERE an existing branch sits in a target shape, not WHY
an arbitrary object should have a branch. No pretrained weights or third-
party geometry generator; accepted older checkpoints remain untouched.
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

from generated_glb_critic import _accessor, _read_glb, inspect

SCHEMA="assetwright-native-branch-v1"
STUDENT="assetwright-owned-branch-site-and-socket-student-v1"
SPLITS={"train":(6,3),"validation":(2,2),"aspect_shift":(2,2)}
CONTROLS=("rise","socket_depth","blend")
V=2730
F=5460
E=8190
PARENT_VERTS=2589
RING=28
TOTAL=520

def expected_stems():
    return {f"{phase}__b{family:02d}__site{site:02d}__v{variant}"
            for phase,(nfamily,nvariant) in SPLITS.items()
            for family in range(1,nfamily+1)
            for site in range(20)
            for variant in range(nvariant)}

def source_recipe(phase,family,site,variant):
    offset={"train":0.,"validation":.005,"aspect_shift":.008}[phase]
    return np.asarray([
        .15+((family*17+site*13+variant*29)%69)/100.+offset,
        .14+((family*23+site*19+variant*31)%70)/100.+offset,
        .13+((family*31+site*17+variant*37)%72)/100.+offset,
    ],dtype=np.float64)

def topology(positions:np.ndarray,indices:list[int])->dict:
    if len(positions)!=V or len(indices)!=3*F:
        raise ValueError("Unexpected welded source vertex/triangle cardinality")
    edges=defaultdict(list)
    incident=defaultdict(set)
    for triangle in range(0,len(indices),3):
        face=tuple(indices[triangle:triangle+3])
        if len(set(face))!=3 or any(v<0 or v>=V for v in face):
            raise ValueError("Invalid native triangle")
        for a,b in zip(face,face[1:]+face[:1]):
            edges[tuple(sorted((a,b)))].append((a,b))
            incident[a].add(b)
            incident[b].add(a)
    if len(edges)!=E or any(len(v)!=2 or v[0][0]!=v[1][1] or
                            v[0][1]!=v[1][0] for v in edges.values()):
        raise ValueError("Open/nonmanifold or inconsistently wound welded branch")
    seen={0}
    queue=deque([0])
    while queue:
        for neighbor in incident[queue.popleft()]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    if len(seen)!=V:
        raise ValueError("Disconnected branch or unindexed isolated vertices")
    euler=V-E+F
    if euler!=0:
        raise ValueError("Parent through-bore genus has been corrupted")
    return {"vertices":V,"edges":E,"faces":F,"components":1,
            "euler_characteristic":euler,"genus":1,
            "welded_branch":True,"all_edges_oppositely_oriented":True}

def morphology(path:Path)->tuple[np.ndarray,dict]:
    doc,blob,_=_read_glb(path)
    if len(doc.get("meshes",[]))!=1 or len(doc["meshes"][0].get("primitives",[]))!=1:
        raise ValueError("Expected one connected original source mesh")
    primitive=doc["meshes"][0]["primitives"][0]
    coords=np.asarray(_accessor(doc,blob,primitive["attributes"]["POSITION"],
                               "positions"),dtype=np.float64)
    indices=_accessor(doc,blob,primitive["indices"],"indices")
    topo=topology(coords,indices)
    # Native boss creation appends FIVE contiguous 28-point rings plus a
    # final socket-floor center after parent 35 patch-interior vertices
    # were removed. This is a known source-topology lesson, not arbitrary
    # topology detection from unknown 3D models.
    if len(coords)-PARENT_VERTS!=5*RING+1:
        raise ValueError("Missing source-homologous branch ring lattice")
    rings=coords[PARENT_VERTS:PARENT_VERTS+5*RING].reshape((5,RING,3))
    means=rings.mean(axis=1)
    direction=(means[2]-means[1])[:2]
    magnitude=np.linalg.norm(direction)
    if magnitude<.03:
        raise ValueError("Collapsed actual side-branch extrusion")
    unit=direction/magnitude
    # Source GLB long axis is Z, with maxZ at longitudinal start.
    longitudinal=float(np.ptp(coords[:,2]))
    if longitudinal<2 or longitudinal>12.1:
        raise ValueError("Invalid native source measured length")
    station_u=float((coords[:,2].max()-means[2,2])/longitudinal)
    end=coords[np.abs(coords[:,2]-coords[:,2].max())<.0001]
    if len(end)<32:
        raise ValueError("No corresponding original solid end section")
    measured_width=float(np.ptp(end[:,0]))
    measured_height=float(np.ptp(end[:,1]))
    min_dimension=min(measured_width,measured_height)
    if min_dimension<.59:
        raise ValueError("Unexpected original base cross-section")
    # Native boss layer 2/3 offsets are at .48 and 1.0 of its total rise.
    height_obs=float(magnitude/.52/min_dimension)
    floor_obs=float(np.linalg.norm(means[2,:2]-means[4,:2]) /
                    (magnitude/.52))
    # Perimeter's tangent-coordinate span is a world-rotation invariant
    # geometry measurement, and recovers how much the support was faired.
    tangent=np.asarray([-unit[1],unit[0]],dtype=np.float64)
    ring_two=rings[1,:,:2]@tangent
    ring_three=rings[2,:,:2]@tangent
    tangential_ratio=float(np.ptp(ring_three)/np.ptp(ring_two))
    if not (.1<height_obs<1.3 and .14<floor_obs<.65
            and .62<tangential_ratio<.96
            and .1<station_u<.9):
        raise ValueError("Physically impossible source branch measurements")
    # 3 location inputs and three continuous-control responses, all
    # measured directly from actual GLB vertex positions.
    values=np.asarray([unit[0],unit[1],station_u,height_obs,
                       floor_obs,tangential_ratio],dtype=np.float64)
    return values,{"topology":topo,
                   "branch_direction":[float(unit[0]),float(unit[1])],
                   "longitudinal_site_u":station_u,
                   "measured_source_width":measured_width,
                   "measured_source_height":measured_height,
                   "branch_height_ratio":height_obs,
                   "blind_socket_depth_fraction":floor_obs,
                   "outer_blend_ratio":tangential_ratio}

def load_dataset(source:Path):
    expected=expected_stems()
    if len(expected)!=TOTAL:
        raise ValueError("Incorrect new original batch cardinality")
    if ({x.stem for x in source.glob("*.glb")}!=expected or
        {x.stem for x in source.glob("*.json")}!=expected):
        raise ValueError("Missing or unexpected source GLBs/manifests")
    rows=[]
    hashes=set()
    for stem in sorted(expected):
        match=re.fullmatch(
            r"(train|validation|aspect_shift)__b(\d\d)__site(\d\d)__v(\d)",
            stem)
        if match is None:
            raise ValueError("Unapproved native branch source name")
        phase,family_text,site_text,variant_text=match.groups()
        family,site,variant=map(int,(family_text,site_text,variant_text))
        nf,nv=SPLITS[phase]
        if not(1<=family<=nf and 0<=site<20 and 0<=variant<nv):
            raise ValueError("Source partition contaminated")
        path=source/(stem+".glb")
        record=json.loads((source/(stem+".json")).read_text())
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        truth=np.asarray([record.get(key) for key in CONTROLS],
                         dtype=np.float64)
        if not(
            record.get("schema")==SCHEMA and
            record.get("case")==stem and record.get("phase")==phase and
            record.get("family")==family and record.get("site")==site and
            record.get("variant")==variant and
            record.get("generator")=="AssetWright-NativeBranchLab" and
            record.get("source_glb_sha256")==sha and
            all(type(record.get(name)) in (int,float) and
                math.isfinite(record[name]) and record[name]>0 for name in
                ("length","width","height")) and
            np.all(np.isfinite(truth)) and
            np.max(np.abs(truth-source_recipe(phase,family,site,variant)))<2e-5):
            raise ValueError("Unverified source hash, labels or authoring provenance")
        if sha in hashes:
            raise ValueError("Duplicate GLB source under different control labels")
        hashes.add(sha)
        audited=inspect(path)
        if not(
            audited["model_sha256"]==sha and
            audited["mesh_parts"]==1 and audited["triangles"]==F and
            audited["invalid_triangles"]==0 and
            audited["boundary_edges"]==0 and
            audited["nonmanifold_edges"]==0 and
            audited["inverted_closed_parts"]==0 and
            audited["parts"][0]["signed_volume"]>0):
            raise ValueError("Original branch source failed independent mesh audit")
        features,geometry=morphology(path)
        rows.append({
            "stem":stem,"phase":phase,"site":site,
            "sha256":sha,"features":features,"target":truth,
            "dims":[record["length"],record["width"],record["height"]],
            "physics":geometry
        })
    return rows

def fit(train:list[dict])->dict:
    if len(train)!=360 or any(x["phase"]!="train" for x in train):
        raise ValueError("Only exactly 360 new training GLBs may fit student")
    if Counter(x["site"] for x in train)!={i:18 for i in range(20)}:
        raise ValueError("Original 20-site learning curriculum unbalanced")
    sites=np.stack([x["features"][:3] for x in train])
    labels=np.array([x["site"] for x in train])
    # Owned nearest-centroid location learner, measured from source positions.
    # No hard-coded site-centers or labels at inference time.
    centroids=np.stack([sites[labels==i].mean(axis=0) for i in range(20)])
    spread=np.maximum(sites.std(axis=0),.08)
    X=np.stack([x["features"][3:] for x in train])
    Y=np.stack([x["target"] for x in train])
    # Native response model must learn nonlinearity in the blended outer wall.
    design=np.column_stack((np.ones(len(X)),X,X[:,2]**2))
    weights=np.linalg.solve(design.T@design +
                            np.diag([0.,.000001,.000001,.000001,.000001]),
                            design.T@Y)
    return {
        "schema":STUDENT,"training_sources":360,"classes":20,
        "source_extractor":"homologous welded boss vertices, not metadata",
        "location_model":"owned_nearest_centroid_source_morphology",
        "site_centroids":centroids.tolist(),"site_scale":spread.tolist(),
        "inverse_model":"owned_multitarget_quadratic_ridge",
        "response_weights":weights.tolist(),
        "strength_controls":list(CONTROLS),
        "source_train_hash_digest":hashlib.sha256(
            "\n".join(sorted(x["sha256"] for x in train)).encode()).hexdigest(),
        "previous_weights_modified":False,
        "android_deployable":False,
        "external_geometry_generator":False
    }

def predict(model:dict,X:np.ndarray):
    x=np.atleast_2d(X)
    locations=x[:,:3]
    prototypes=np.asarray(model["site_centroids"])
    scale=np.asarray(model["site_scale"])
    errors=((locations[:,None,:]-prototypes[None,:,:])/scale)**2
    sites=np.argmin(errors.sum(axis=2),axis=1)
    responses=x[:,3:]
    design=np.column_stack((np.ones(len(responses)),responses,responses[:,2]**2))
    continuous=np.clip(design@np.asarray(model["response_weights"]),0,1)
    return sites,continuous

def score(model:dict,rows:list[dict],phase:str):
    if not rows or any(x["phase"]!=phase for x in rows):
        raise ValueError("Attempted evaluation on incorrect split")
    X=np.stack([x["features"] for x in rows])
    predicted_site,continuous=predict(model,X)
    labels=np.array([x["site"] for x in rows])
    true=np.stack([x["target"] for x in rows])
    correct=predicted_site==labels
    errors=np.abs(continuous-true)
    baseline=float(np.abs(true-.5).mean())
    report={
        "sources":len(rows),"exact_site_accuracy":float(correct.mean()),
        "mean_control_mae":float(errors.mean()),
        "max_control_error":float(errors.max()),
        "per_strength_mae":{k:float(errors[:,i].mean())
                            for i,k in enumerate(CONTROLS)},
        "constant_strength_baseline_mae":baseline,
        "per_site_correct":{str(i):int(np.sum(correct & (labels==i)))
                            for i in range(20)},
        "per_site_total":len(rows)//20
    }
    cases=[{
        "stem":row["stem"],"source_sha256":row["sha256"],
        "true_site":row["site"],"estimated_site":int(site),
        "true_strengths":row["target"].tolist(),
        "estimated_strengths":guess.tolist()
    } for row,site,guess in zip(rows,predicted_site,continuous)]
    return report,cases

def gates(normal,shift):
    return {
        "heldout_location_accuracy":normal["exact_site_accuracy"]>=.95,
        "aspect_location_accuracy":shift["exact_site_accuracy"]>=.90,
        "heldout_site_min_recall":all(v>=3 for v in normal["per_site_correct"].values()),
        "aspect_site_min_recall":all(v>=3 for v in shift["per_site_correct"].values()),
        "heldout_control_mae":normal["mean_control_mae"]<=.020,
        "aspect_control_mae":shift["mean_control_mae"]<=.030,
        "heldout_per_control":all(v<=.028 for v in normal["per_strength_mae"].values()),
        "aspect_per_control":all(v<=.040 for v in shift["per_strength_mae"].values()),
        "heldout_max_error":normal["max_control_error"]<=.09,
        "aspect_max_error":shift["max_control_error"]<=.13,
        "beats_constant_baseline_normal":
            normal["constant_strength_baseline_mae"]-normal["mean_control_mae"]>=.12,
        "beats_constant_baseline_aspect":
            shift["constant_strength_baseline_mae"]-shift["mean_control_mae"]>=.12
    }

def run(source:Path,out:Path):
    rows=load_dataset(source)
    train=[x for x in rows if x["phase"]=="train"]
    val=[x for x in rows if x["phase"]=="validation"]
    shift=[x for x in rows if x["phase"]=="aspect_shift"]
    if tuple(map(len,(train,val,shift)))!=(360,80,80):
        raise ValueError("Unexpected branch study partitions")
    model=fit(train)
    val_metrics,val_cases=score(model,val,"validation")
    shift_metrics,shift_cases=score(model,shift,"aspect_shift")
    checks=gates(val_metrics,shift_metrics)
    success=all(checks.values())
    result={
        "schema":"assetwright-native-branch-placement-study-v1",
        "status":"passed_development_only" if success else "rejected",
        "original_kotlin_glbs":TOTAL,"training_source_glbs":360,
        "heldout_dimension_glbs":80,"heldout_aspect_glbs":80,
        "all_source_sha256_unique":True,
        "connected_manifold_genus_one_audits":TOTAL,
        "kind":"single native side boss with real blind socket and retained main through-bore",
        "site_choices":20,
        "dimension_holdout":val_metrics,"aspect_holdout":shift_metrics,
        "checks":checks,"human_visual_approval":False,
        "android_deployed":False,"prior_checkpoints_unchanged":True,
        "limitations":"Shape-based location recovery of known native branch scaffold; not freeform semantic placement planning or real three-way through-channel."
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"branch_report.json").write_text(json.dumps(result,indent=2)+"\n")
    (out/"candidate_branch_student.json").write_text(json.dumps(model,indent=2)+"\n")
    (out/"heldout_predictions.json").write_text(json.dumps(
        {"validation":val_cases,"aspect_shift":shift_cases},indent=2)+"\n")
    with (out/"student_branch_commands.tsv").open("w") as f:
        for row,pred in zip([*val,*shift],[*val_cases,*shift_cases]):
            assert row["stem"]==pred["stem"]
            f.write("\t".join((pred["stem"],str(pred["estimated_site"]),
                ",".join(f"{v:.9f}" for v in pred["estimated_strengths"]),
                ",".join(str(v) for v in row["dims"])))+"\n")
    print(json.dumps({
        "status":result["status"],"dimension":val_metrics,"aspect":shift_metrics,
        "checks":checks
    },indent=2))
    if not success:
        raise SystemExit("Native branch student rejected: fixed acceptance thresholds")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    run(args.source,args.out)

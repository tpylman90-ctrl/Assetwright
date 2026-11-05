"""Source-hashed CAD STL geometry descriptors for AssetWright's own Mini AI.

Licensed Autodesk Zero-to-CAD STL is a transient numerical *teacher* only.
Never execute downloaded CadQuery, import a reference STL into the app, or
claim a predicted descriptor is a generated professional-quality mesh.

All outputs are normalized numeric measurements and source hashes.
STL geometry remains in memory; only safe records leave this function.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

from deep_dino_curriculum import numeric_cad_features, NUMERIC_SCHEMA
from zero_to_cad_ingest import DATASET,LICENSE,SCHEMA,dataset_iterator,parse_row

GEOMETRY_SCHEMA="assetwright-cad-stl-surface-teacher-v1"
TARGETS=("middle_over_major","minor_over_major","surface_over_box",
         "strong_crease_edge_fraction","moderate_crease_edge_fraction")
MAX_STL_BYTES=5_500_000
MAX_TRIANGLES=100_000
# Prior CAD study inspected validation first 656 scans, and DINO work
# sampled 240..336. Start beyond this region with a separate cohort.
ALLOWED_OFFSETS={"train":(2200,4000),"validation":(1500,4000)}

def safe_stl_bytes(raw:object)->bytes:
    if isinstance(raw,dict):
        raw=raw.get("bytes")
    if isinstance(raw,bytearray):
        raw=bytes(raw)
    if not isinstance(raw,bytes) or not 134<=len(raw)<=MAX_STL_BYTES:
        raise ValueError("Missing/oversize reference STL")
    return raw

def decode_stl(source:bytes)->np.ndarray:
    """Read binary STL vertices without running or importing untrusted code."""
    if len(source)<84:
        raise ValueError("Truncated binary STL")
    tri_count=int.from_bytes(source[80:84],"little")
    if tri_count<8 or tri_count>MAX_TRIANGLES:
        raise ValueError("Invalid bounded STL triangle count")
    if len(source)!=84+50*tri_count:
        raise ValueError("Not exact binary STL: reject ambiguous ASCII/trailing files")
    dtype=np.dtype([("normal","<f4",(3,)),("vertex","<f4",(3,3)),("tag","<u2")])
    vertices=np.frombuffer(source,dtype=dtype,offset=84,count=tri_count)["vertex"]
    if not np.isfinite(vertices).all():
        raise ValueError("Nonfinite STL geometry")
    positions=vertices.astype(np.float64,copy=True)
    if np.abs(positions).max()>1e8:
        raise ValueError("Unbounded STL coordinates")
    return positions

def descriptors(triangles:np.ndarray)->tuple[list[float],dict]:
    points=triangles.reshape(-1,3)
    mins=points.min(axis=0)
    maxs=points.max(axis=0)
    size=maxs-mins
    if size.min()<=1e-7 or not np.isfinite(size).all():
        raise ValueError("Degenerate 3D bounding dimensions")
    largest=float(size.max())
    aspect=np.sort(size)/largest
    a=triangles[:,1]-triangles[:,0]
    b=triangles[:,2]-triangles[:,0]
    cross=np.cross(a,b)
    lengths=np.linalg.norm(cross,axis=1)
    if (lengths<=1e-12*largest*largest).mean()>.04:
        raise ValueError("Excessive source degenerate triangles")
    good=lengths>1e-12*largest*largest
    normals=np.zeros_like(cross)
    normals[good]=cross[good]/lengths[good,None]
    total_area=float(lengths.sum()*.5)
    bbox_area=float(2*(size[0]*size[1]+size[0]*size[2]+size[1]*size[2]))
    # Scale-invariant area-ratio; complex/concave objects may exceed 1.
    area_ratio=min(4.,total_area/bbox_area)

    # STL duplicates face corners; weld only for measurement with a
    # documented 1e-5 relative geometric tolerance, not for authoring.
    quantum=largest*1e-5
    ids=np.unique(np.rint(points/quantum).astype(np.int64),
                  axis=0,return_inverse=True)[1].reshape(-1,3)
    edges=np.concatenate((ids[:,[0,1]],ids[:,[1,2]],ids[:,[2,0]]))
    edges.sort(axis=1)
    order=np.lexsort((edges[:,1],edges[:,0]))
    sorted_edges=edges[order]
    starts=np.concatenate(([0],np.flatnonzero(np.any(
        sorted_edges[1:]!=sorted_edges[:-1],axis=1))+1))
    counts=np.diff(np.concatenate((starts,[len(order)])))
    repeated=np.flatnonzero(counts==2)
    if len(repeated)<int(triangles.shape[0]*.15):
        raise ValueError("Insufficient connected STL edges for curvature lesson")
    # Correct correspondence with concatenated three face-edge blocks.
    tri_ids=np.tile(np.arange(len(triangles)),3)
    first=order[starts[repeated]]
    second=order[starts[repeated]+1]
    cosine=np.einsum("ij,ij->i",normals[tri_ids[first]],normals[tri_ids[second]])
    cosine=np.clip(cosine,-1.,1.)
    stable=(good[tri_ids[first]] & good[tri_ids[second]])
    if stable.sum()<int(triangles.shape[0]*.15):
        raise ValueError("Insufficient valid shared triangle edges")
    cos_valid=cosine[stable]
    # Measured seam normal variation proxies, not mathematically exact
    # G1/G2 curvature and not CAD B-rep surface-edge labels.
    crease30=float(np.mean(cos_valid<math.cos(math.pi/6)))
    crease15=float(np.mean(cos_valid<math.cos(math.pi/12)))
    features=[
        round(float(aspect[1]),8),round(float(aspect[0]),8),
        round(area_ratio,8),round(crease30,8),round(crease15,8)
    ]
    if not all(math.isfinite(x) and 0<=x<=4 for x in features):
        raise ValueError("Nonfinite physical source surface measurements")
    return features,{
        "triangles":int(len(triangles)),
        "vertices_after_measurement_weld":int(ids.max()+1),
        "unique_edges_after_measurement_weld":int(len(starts)),
        "paired_edges":int((counts==2).sum()),
        "boundary_edges":int((counts==1).sum()),
        "overused_edges":int((counts>2).sum()),
        "normal_angles":"local adjacent STL triangle normals; 15 and 30 degrees",
        "measurement_tolerance_relative_to_max_extent":1e-5,
        "bounding_surface_area_ratio":round(area_ratio,8)
    }

def collect(split:str,revision:str,offset:int,count:int,scan:int)->dict:
    if split not in ("train","validation"):
        raise ValueError("Only original official train and validation")
    if not isinstance(revision,str) or not re.fullmatch(r"[a-f0-9]{40}",revision):
        raise ValueError("Pinned licensed source SHA required")
    lower,upper=ALLOWED_OFFSETS[split]
    if not lower<=offset<=upper:
        raise ValueError("Evaluation cohorts must not reuse exposed source prefix")
    if not 32<=count<=550 or not count<=scan<=1600 or offset+scan>6500:
        raise ValueError("Unbounded STL study")
    rows=[];ids=set();hashes=set();meshes=set();rejected=Counter();scanned=0
    for idx,raw in enumerate(dataset_iterator(split,revision)):
        if idx<offset:continue
        if len(rows)>=count or scanned>=scan:break
        scanned+=1
        row,reason=parse_row(raw,split)
        if row is None:
            rejected[reason]+=1;continue
        if row["source_id"] in ids or row["code_sha256"] in hashes:
            rejected["duplicate_source"]+=1;continue
        try:
            source=safe_stl_bytes(raw.get("stl_file"))
            mesh_sha=hashlib.sha256(source).hexdigest()
            if mesh_sha in meshes:
                rejected["duplicate_mesh"]+=1;continue
            geometry,physics=descriptors(decode_stl(source))
        except (ValueError,TypeError,MemoryError) as error:
            rejected["bad_or_excessive_stl"]+=1;continue
        ids.add(row["source_id"]);hashes.add(row["code_sha256"]);meshes.add(mesh_sha)
        rows.append({
            "source_id":row["source_id"],"code_sha256":row["code_sha256"],
            "stl_sha256":mesh_sha,"split":split,
            "operations":row["operations"],
            "safe_numeric_cad_features":numeric_cad_features(raw.get("cadquery_file")),
            "surface_target":geometry,"surface_audit":physics
        })
    result={
        "schema":GEOMETRY_SCHEMA,"dataset":DATASET,"license":LICENSE,
        "dataset_revision":revision,"official_split":split,
        "source_offset":offset,"scanned":scanned,"accepted":len(rows),
        "records":rows,"target_names":list(TARGETS),
        "numeric_feature_schema":NUMERIC_SCHEMA,
        "rejected":dict(rejected),
        "downloaded_scripts_executed":False,
        "downloaded_meshes_exported_as_native":False,
        "mesh_bytes_retained":False
    }
    if len(rows)<count:
        raise ValueError(f"Insufficient original STL descriptors: {len(rows)}/{count}; scan={scanned}; rejections={dict(rejected)}")
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split",choices=("train","validation"),required=True)
    p.add_argument("--revision",required=True)
    p.add_argument("--offset",type=int,required=True)
    p.add_argument("--count",type=int,required=True)
    p.add_argument("--scan-limit",type=int,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    data=collect(args.split,args.revision,args.offset,args.count,args.scan_limit)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps({k:v for k,v in data.items() if k!="records"},indent=2))

if __name__=="__main__":main()

#!/usr/bin/env python3
"""Independent structural quality critic for ORIGINAL Assetwright-generated GLBs.

This validates real exported vertex/index buffers, mesh topology and named
part positions. The critic cannot judge artistic beauty, and does not create
semantic labels or use source datasets as candidate construction targets.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

MAX_BYTES = 15 * 1024 * 1024
MAX_TRIANGLES = 250_000
MAX_PARTS = 200
MAX_ACCESSOR_ITEMS = 900_000
TRIANGLE_EPS_SQUARED = 1e-14

def _read_glb(path: Path) -> tuple[dict,bytes,str]:
    raw=path.read_bytes()
    if not 32 <= len(raw) <= MAX_BYTES:
        raise ValueError("GLB size outside limits")
    if raw[:4]!=b"glTF":
        raise ValueError("Missing GLB header")
    magic,version,length=struct.unpack_from("<III",raw,0)
    if magic!=0x46546C67 or version!=2 or length!=len(raw):
        raise ValueError("Unsupported or truncated GLB")
    off=12
    doc=None
    blob=None
    while off+8<=len(raw):
        n,kind=struct.unpack_from("<II",raw,off)
        off+=8
        if n%4 or off+n>len(raw):
            raise ValueError("Invalid GLB chunk")
        if kind==0x4e4f534a:
            if doc is not None: raise ValueError("Duplicate JSON")
            doc=json.loads(raw[off:off+n].decode("utf-8"))
        if kind==0x004e4942:
            if blob is not None: raise ValueError("Duplicate binary")
            blob=raw[off:off+n]
        off+=n
    if off!=len(raw) or not isinstance(doc,dict) or blob is None:
        raise ValueError("Missing GLB chunks")
    if doc.get("asset",{}).get("version")!="2.0":
        raise ValueError("Not glTF 2.0")
    if doc.get("buffers",[{}])[0].get("byteLength",0)>len(blob):
        raise ValueError("GLB buffer missing bytes")
    if len(doc.get("meshes",[]))>MAX_PARTS:
        raise ValueError("Too many meshes")
    return doc,blob,hashlib.sha256(raw).hexdigest()

def _accessor(doc:dict,blob:bytes,accessor_id:int,kind:str):
    accessors=doc.get("accessors",[])
    if type(accessor_id) is not int or not 0<=accessor_id<len(accessors):
        raise ValueError("Bad accessor index")
    a=accessors[accessor_id]
    if "sparse" in a:
        raise ValueError("Sparse accessors not supported")
    count=a.get("count")
    if type(count) is not int or not 0<count<=MAX_ACCESSOR_ITEMS:
        raise ValueError("Invalid accessor count")
    if kind=="positions":
        if a.get("type")!="VEC3" or a.get("componentType")!=5126:
            raise ValueError("Positions must be float32 VEC3")
        fmt="fff"
    else:
        fmt={5121:"B",5123:"H",5125:"I"}.get(a.get("componentType"))
        if a.get("type")!="SCALAR" or not fmt:
            raise ValueError("Unsupported index format")
    views=doc.get("bufferViews",[])
    view_id=a.get("bufferView")
    if type(view_id) is not int or not 0<=view_id<len(views):
        raise ValueError("Missing buffer view")
    view=views[view_id]
    if view.get("buffer")!=0:
        raise ValueError("External buffers forbidden")
    begin=view.get("byteOffset",0)
    length=view.get("byteLength")
    offset=a.get("byteOffset",0)
    size=struct.calcsize("<"+fmt)
    stride=view.get("byteStride",size)
    if any(type(v) is not int for v in (begin,length,offset,stride)):
        raise ValueError("Invalid buffer offsets")
    if min(begin,length,offset,stride)<0 or stride<size:
        raise ValueError("Negative or narrow buffer region")
    if offset+(count-1)*stride+size>length or begin+length>len(blob):
        raise ValueError("Accessor exceeds buffer bounds")
    unpacker=struct.Struct("<"+fmt)
    result=[unpacker.unpack_from(blob,begin+offset+i*stride) for i in range(count)]
    if kind=="positions":
        if any(not math.isfinite(x) or abs(x)>10000 for row in result for x in row):
            raise ValueError("Invalid vertex coordinates")
        return result
    return [x[0] for x in result]

def _extent(points:list)->tuple:
    return (tuple(min(p[axis] for p in points) for axis in range(3)),
            tuple(max(p[axis] for p in points) for axis in range(3)))

def inspect(path:Path)->dict:
    doc,blob,sha=_read_glb(path)
    parts=[]
    triangle_total=0
    invalid_triangles=0
    nonmanifold_edges=0
    open_edges=0
    inverted_closed_parts=0
    # No transforms supported yet: native Assetwright exports identity nodes.
    if any(any(k in node for k in ("matrix","rotation","scale","translation"))
           for node in doc.get("nodes",[])):
        raise ValueError("Transformed glTF nodes need separate world-space audit")
    for mesh in doc.get("meshes",[]):
        name=str(mesh.get("name",""))[:100]
        polygons=0
        vertices=[]
        edge_counts=Counter()
        signed_volume=0.
        invalid=0
        for primitive in mesh.get("primitives",[]):
            if primitive.get("mode",4)!=4 or "indices" not in primitive:
                raise ValueError("Only indexed triangle meshes supported")
            coords=_accessor(doc,blob,primitive.get("attributes",{}).get("POSITION"),"positions")
            indices=_accessor(doc,blob,primitive["indices"],"indices")
            if len(indices)%3:
                raise ValueError("Index count not divisible by three")
            if any(i>=len(coords) for i in indices):
                raise ValueError("Invalid vertex index")
            polygons+=len(indices)//3
            vertices.extend(coords)
            if polygons>MAX_TRIANGLES:
                raise ValueError("Unbounded mesh")
            for j in range(0,len(indices),3):
                a,b,c=indices[j:j+3]
                x,y,z=coords[a],coords[b],coords[c]
                u=tuple(y[k]-x[k] for k in range(3))
                v=tuple(z[k]-x[k] for k in range(3))
                cross=(u[1]*v[2]-u[2]*v[1],
                       u[2]*v[0]-u[0]*v[2],
                       u[0]*v[1]-u[1]*v[0])
                area2=sum(q*q for q in cross)
                if len({a,b,c})<3 or area2<TRIANGLE_EPS_SQUARED:
                    invalid+=1
                signed_volume+=sum(x[k]*cross[k] for k in range(3))/6.
                for edge in ((a,b),(b,c),(c,a)):
                    edge_counts[tuple(sorted(edge))]+=1
        if not vertices or polygons<1:
            raise ValueError("Empty geometry part")
        (minimum,maximum)=_extent(vertices)
        triangle_total+=polygons
        invalid_triangles+=invalid
        boundaries=sum(v==1 for v in edge_counts.values())
        overused=sum(v>2 for v in edge_counts.values())
        open_edges+=boundaries
        nonmanifold_edges+=overused
        # Only check volume of actually closed components; open panels need not
        # be watertight. This is a heuristic, not proof of collision-free mesh.
        if boundaries==0 and overused==0 and signed_volume < -1e-6:
            inverted_closed_parts+=1
        parts.append({"name":name,"triangles":polygons,"invalid_triangles":invalid,
                      "boundary_edges":boundaries,"nonmanifold_edges":overused,
                      "signed_volume":round(signed_volume,6),
                      "min":[round(v,6) for v in minimum],
                      "max":[round(v,6) for v in maximum]})
    if triangle_total>MAX_TRIANGLES:
        raise ValueError("Triangle budget exceeded")
    return {
        "schema":"assetwright-generated-glb-mesh-audit-v1",
        "model_sha256":sha,
        "triangles":triangle_total,
        "mesh_parts":len(parts),
        "invalid_triangles":invalid_triangles,
        "boundary_edges":open_edges,
        "nonmanifold_edges":nonmanifold_edges,
        "inverted_closed_parts":inverted_closed_parts,
        "parts":parts
    }

def _centroid_axis(p:dict,axis:int)->float:
    return (p["min"][axis]+p["max"][axis])/2.

def evaluate(audit:dict,expected:dict)->dict:
    if expected.get("schema")!="assetwright-generated-vehicle-target-v1":
        raise ValueError("Unsupported evaluation target")
    if not expected.get("original_procedural_asset",False):
        raise ValueError("Only owned original procedural generations are permitted")
    lift=expected["lift_cells"]
    drive=expected["drive_count"]
    mount=expected["mount"]
    roof=expected["roof_height"]
    if type(lift) is not int or lift not in (2,4,6):
        raise ValueError("Invalid lift target")
    if type(drive) is not int or drive not in (1,2,3):
        raise ValueError("Invalid propulsion target")
    if mount not in ("tucked","exposed") or type(roof) not in (int,float):
        raise ValueError("Invalid construction metadata")
    by_name=defaultdict(list)
    for part in audit["parts"]:
        by_name[part["name"]].append(part)
    body=by_name.get("Sculpted continuous body",[])
    cabin=by_name.get("Bonded panoramic canopy",[])
    pads=by_name.get("Underslung repulsor",[])
    brackets=by_name.get("Repulsor mount bracket",[])
    engines=[p for p in audit["parts"] if p["name"].endswith("housing") and
             p["name"] in ("Central booster housing","Rear drive housing")]
    # glTF is Y-up. Native 3D Z coordinate -> glTF Y coordinate.
    canopy_clearance=(cabin[0]["max"][1]-body[0]["max"][1] if len(cabin)==1 and len(body)==1 else None)
    cabin_top=cabin[0]["max"][1] if len(cabin)==1 else None
    body_half_width=(max(abs(body[0]["min"][0]),abs(body[0]["max"][0])) if len(body)==1 else None)
    outboard_centers=[abs(_centroid_axis(p,0)) for p in pads]
    alignment=[]
    if len(pads)==len(brackets):
        for pad,arm in zip(pads,brackets):
            cx=_centroid_axis(pad,0)
            alignment.append(arm["min"][0]-0.12<=cx<=arm["max"][0]+0.12)
    checks={
       "part_count_matches":len(pads)==lift and len(brackets)==lift and len(engines)==drive,
       "canopy_clearance":canopy_clearance is not None and canopy_clearance>=.235,
       "roof_bound":cabin_top is not None and abs(cabin_top-roof)<=.035,
       "lift_mount_location":(
           body_half_width is not None and len(pads)==lift and
           (all(c>body_half_width+.10 for c in outboard_centers)
            if mount=="exposed" else all(c<body_half_width for c in outboard_centers))
       ),
       "brackets_reach_units":len(alignment)==lift and all(alignment),
       "no_degenerate_triangles":audit["invalid_triangles"]==0,
       "no_overused_edges":audit["nonmanifold_edges"]==0,
       "triangles_within_mobile_budget":0<audit["triangles"]<=12000,
    }
    hard=["part_count_matches","canopy_clearance","roof_bound","lift_mount_location",
          "brackets_reach_units","no_degenerate_triangles","no_overused_edges",
          "triangles_within_mobile_budget"]
    # Rank only the structurally valid candidates, not beauty or uniqueness.
    passed=all(checks[name] for name in hard)
    margin=min(max((canopy_clearance or 0)-.235,0),.20)
    score=(round(0.8 + min(margin, .18)/.18*.12 +
                 max(0,1-audit["triangles"]/12000)*.08,6) if passed else 0.)
    return {
       "schema":"assetwright-generated-geometry-evaluation-v1",
       "model_sha256":audit["model_sha256"],
       "passed":passed,"score":score,
       "checks":checks,
       "measurements":{
           "canopy_clearance":round(canopy_clearance,5) if canopy_clearance is not None else None,
           "roof_measured":cabin_top,
           "body_half_width":body_half_width,
           "part_count":audit["mesh_parts"],
           "triangles":audit["triangles"]
       },
       "limitations":"Geometric screening only; no visual realism, symmetry aesthetics, source similarity, real collision proof or semantic teacher.",
       "training_label_status":"benchmark_score_not_verified_supervision"
    }

def main():
    cmd=argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("--glb",type=Path,required=True)
    cmd.add_argument("--target",type=Path,required=True)
    cmd.add_argument("--out",type=Path,required=True)
    args=cmd.parse_args()
    result=evaluate(inspect(args.glb),json.loads(args.target.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="checks"},indent=2))
    if not result["passed"]:
        raise SystemExit(2)

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Deterministic CPU diagnostic clay and wire previews of OWN original V2 GLBs.

Rendering ONLY, not mesh generation or a substitute for human inspection.
Uses glTF source vertices/triangles and Python Pillow without Blender/GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from generated_glb_critic import _read_glb, _accessor, inspect

VIEW_DIRECTIONS = {
    "front": (0.0, 1.9, 9.0),
    "side": (9.0, 2.2, 0.0),
    "top": (0.001, 9.0, 0.001),
    "rear": (0.0, 2.0, -9.0),
    "front_three_quarter": (6.4, 3.2, 8.0),
}
FAMILIES = ("rockerdev_a", "rockerdev_b")
VARIANTS = ("baseline", "s900", "combined_four")
W, H = 1050, 770

def subtract(a, b):
    return tuple(x-y for x,y in zip(a,b))

def dot(a, b):
    return sum(x*y for x,y in zip(a,b))

def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])

def normalized(v):
    norm=math.sqrt(dot(v,v))
    if norm < 1e-9: raise ValueError("Undefined camera/normal vector")
    return tuple(x/norm for x in v)

def load_meshes(path):
    doc, blob, sha = _read_glb(path)
    if inspect(path)["model_sha256"] != sha:
        raise ValueError("Source GLB provenance failure")
    meshes=[]
    for mesh in doc.get("meshes",[]):
        for primitive in mesh.get("primitives",[]):
            verts=_accessor(doc,blob,primitive["attributes"]["POSITION"],"positions")
            faces=_accessor(doc,blob,primitive["indices"],"indices")
            mat=doc["materials"][primitive["material"]]["pbrMetallicRoughness"]
            rgba=mat["baseColorFactor"]
            color=tuple(round(max(0,min(1,x))*255) for x in rgba[:3])
            meshes.append((str(mesh.get("name","")),verts,faces,color))
    return meshes,sha

def render(meshes, view, mode, title, destination):
    all_points=[p for _,vertices,_,_ in meshes for p in vertices]
    bounds=[(min(p[i] for p in all_points),max(p[i] for p in all_points))
            for i in range(3)]
    target=tuple((lo+hi)/2 for lo,hi in bounds)
    forward=normalized(tuple(-q for q in VIEW_DIRECTIONS[view]))
    nominal_up=(0.,0.,1.) if view=="top" else (0.,1.,0.)
    right=normalized(cross(forward,nominal_up))
    up=cross(right,forward)
    light=normalized((-.5,.9,1.0))
    # Fit each orthographic camera to the actual asset rather than leaving
    # vehicles tiny in the review. The same family baseline/modified spans
    # are close enough for comparable human inspection.
    projected=[(dot(subtract(v,target),right),dot(subtract(v,target),up))
               for v in all_points]
    span_x=max(x for x,_ in projected)-min(x for x,_ in projected)
    span_y=max(y for _,y in projected)-min(y for _,y in projected)
    scale=min((W-140)/max(span_x,.01),(H-140)/max(span_y,.01),175.0)
    def project(v):
        p=subtract(v,target)
        return (W/2+scale*dot(p,right), H/2-scale*dot(p,up),
                dot(p,forward))
    triangles=[]
    for name,verts,indices,color in meshes:
        proj=[project(v) for v in verts]
        for i in range(0,len(indices),3):
            a,b,c=indices[i:i+3]
            pa,pb,pc=proj[a],proj[b],proj[c]
            xyz=[verts[a],verts[b],verts[c]]
            n=cross(subtract(xyz[1],xyz[0]),subtract(xyz[2],xyz[0]))
            if dot(n,n)<1e-14: continue
            normal=normalized(n)
            # Diagnostic directional light shows curvature direction;
            # double-sided abs(n dot light) previously flattened shadows.
            shade=.36+.64*max(0.,dot(normal,light))
            if mode=="clay":
                base=(80,101,120) if "canopy" in name.lower() else (
                    (92,103,118) if "keel" in name.lower() or
                    "bracket" in name.lower() else (176,187,199))
            else:
                base=(46,57,73)
            shaded=tuple(min(255,round(channel*shade)) for channel in base)
            triangles.append(((pa[2]+pb[2]+pc[2])/3,
                              ((pa[0],pa[1]),(pb[0],pb[1]),(pc[0],pc[1])),
                              shaded))
    triangles.sort(key=lambda item:item[0],reverse=True)
    image=Image.new("RGB",(W,H),(20,26,37))
    draw=ImageDraw.Draw(image)
    for _,coords,fill in triangles:
        draw.polygon(coords,fill=fill)
        if mode=="wire":
            draw.line((coords[0],coords[1],coords[2],coords[0]),
                      fill=(146,198,220),width=1)
    draw.rectangle((18,18,W-18,H-18),outline=(55,70,89),width=2)
    font=ImageFont.load_default()
    draw.text((32,32),title,fill=(237,243,250),font=font)
    draw.text((32,H-44),
              "ORIGINAL KOTLIN GLB  |  ORTHOGRAPHIC DIAGNOSTIC  |  NOT PBR",
              fill=(174,190,204),font=font)
    destination.parent.mkdir(parents=True,exist_ok=True)
    image.save(destination,optimize=True)

def run(source, out):
    out.mkdir(parents=True,exist_ok=True)
    manifest={"schema":"assetwright-rocker-v2-diagnostic-renders-v1",
              "source":"original-kotlin-MiniGeometry-GlbWriter",
              "render_type":"CPU orthographic diagnostic, not beauty approval",
              "images":[]}
    for family in FAMILIES:
        for variant in VARIANTS:
            stem=family+"__"+variant
            mesh_path=source/(stem+".glb")
            meta=json.loads((source/(stem+".json")).read_text())
            meshes,sha=load_meshes(mesh_path)
            if meta.get("source_glb_sha256")!=sha or meta.get("case")!=stem:
                raise ValueError("Unverified original GLB: "+stem)
            for view in VIEW_DIRECTIONS:
                for mode in ("clay","wire"):
                    filename=stem+"__"+view+"__"+mode+".png"
                    path=out/filename
                    render(meshes,view,mode,
                           family+" | "+variant+" | "+view+" | "+mode,path)
                    manifest["images"].append({
                        "file":filename,"source_glb_sha256":sha,
                        "png_sha256":hashlib.sha256(path.read_bytes()).hexdigest()
                    })
    (out/"render_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    if len(manifest["images"])!=60:
        raise ValueError("Incomplete original source preview set")
    print("Rendered 60 source-verified orthographic diagnostic views")
    return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    run(args.source,args.out)

"""Visual review of original and student-reconstructed continuous native hulls.

This rasterizer does NOT create or alter geometry. Its inputs are only
source-hashed AssetWright Kotlin GLBs. No aesthetic claims are automatic.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from render_native_rocker_v2 import load_meshes, render

CASES=(
    "train__ctrain03__p02__v1",
    "train__ctrain09__p15__v3",
    "validation__cval2__p02__v1",
    "validation__cval4__p15__v0",
    "aspect_shift__cshift3__p12__v1",
    "aspect_shift__cshift4__p18__v0"
)

def run(source:Path,recon:Path,out:Path)->dict:
    out.mkdir(parents=True,exist_ok=True)
    rendered=[]
    for stem in CASES:
        for origin in ("target","student"):
            if origin=="student" and stem.startswith("train__"):
                continue
            path=(source if origin=="target" else recon)/(stem+".glb")
            meshes,sha=load_meshes(path)
            if origin=="target":
                meta=json.loads(path.with_suffix(".json").read_text())
                if sha!=meta["source_glb_sha256"]:
                    raise ValueError("Unverified original GLB in visual review")
            else:
                if sha!=path.with_suffix(".sha256").read_text().strip():
                    raise ValueError("Unverified student reconstructed GLB")
            for view in ("side","front_three_quarter","top"):
                for mode in ("clay","wire"):
                    file=out/(stem+"__"+origin+"__"+view+"__"+mode+".png")
                    render(meshes,view,mode,
                           stem+" | "+origin+" | "+view+" | "+mode,file)
                    rendered.append({
                        "file":file.name,"role":origin,
                        "source_glb_sha256":sha,
                        "image_sha256":hashlib.sha256(file.read_bytes()).hexdigest()
                    })
    result={"schema":"assetwright-composition-review-v1",
            "count":len(rendered),"status":"human_review_required",
            "purpose":"Actual geometry target and own reconstructed native GLB. Not PBR.",
            "images":rendered}
    if len(rendered)!=60:
        raise ValueError("Incomplete composition clay/wire 60-view proof")
    (out/"render_manifest.json").write_text(json.dumps(result,indent=2)+"\n")
    print(f"Generated {len(rendered)} source-hashed composition diagnostic PNGs")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--reconstructed",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    run(a.source,a.reconstructed,a.out)

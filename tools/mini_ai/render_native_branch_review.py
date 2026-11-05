"""Original geometry-only CPU clay/wire review of connected blind sockets.

This changes NO mesh vertices and cannot certify production visual quality.
Only the source-hashed native Kotlin target and student GLBs are displayed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from render_native_rocker_v2 import load_meshes, render

TRAIN=("train__b02__site07__v1","train__b06__site15__v0")
HELDOUT=("validation__b01__site03__v1",
         "validation__b02__site14__v0",
         "aspect_shift__b01__site11__v1",
         "aspect_shift__b02__site18__v0")
VIEWS=("front","side","top","front_three_quarter")
MODES=("clay","wire")

def run(source:Path,reconstruction:Path,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    files=[]
    for stem in (*TRAIN,*HELDOUT):
        roles=("target",) if stem in TRAIN else ("target","student")
        for role in roles:
            glb=(source if role=="target" else reconstruction)/(stem+".glb")
            meshes,source_hash=load_meshes(glb)
            if role=="target":
                manifest=json.loads(glb.with_suffix(".json").read_text())
                if manifest["source_glb_sha256"]!=source_hash:
                    raise ValueError("Unverified original native branch source")
            elif glb.with_suffix(".sha256").read_text().strip()!=source_hash:
                raise ValueError("Unverified native student reconstruction")
            for view in VIEWS:
                for mode in MODES:
                    output=out/(stem+"__"+role+"__"+view+"__"+mode+".png")
                    render(meshes,view,mode,
                           stem+" | "+role+" | "+view+" | "+mode,output)
                    files.append({
                        "file":output.name,"case":stem,"role":role,
                        "view":view,"mode":mode,
                        "original_glb_sha256":source_hash,
                        "image_sha256":hashlib.sha256(output.read_bytes()).hexdigest()
                    })
    if len(files)!=80:
        raise ValueError("Incomplete original source-hashed junction visual review")
    report={
        "schema":"assetwright-native-branch-visual-review-v1",
        "images":files,"render_count":len(files),
        "status":"diagnostic_requires_human_approval",
        "no_external_geometry_generator":True,
        "limitations":"Simple blind boss on original through-bore; no CSG, arbitrary NURBS fillet, or production review."
    }
    (out/"review_manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"Rendered {len(files)} original source-verified branch views")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--reconstructed",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    run(args.source,args.reconstructed,args.out)

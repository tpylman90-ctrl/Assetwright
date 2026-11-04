"""Render ORIGINAL advanced-form GLBs for human clay/wire inspection.

No geometry generation happens here; all source meshes are verified Kotlin
exports and color is diagnostic rather than a production PBR claim.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from render_native_rocker_v2 import load_meshes, render

OPS=("section_loft","tangent_sweep","section_twist",
     "superellipse_profile","lower_recess","ribbed_fairing")
CASES=(
    ("train","advtrain02",("s170","s800")),
    ("train","advtrain11",("s170","s800")),
    ("aspect_shift","advshift6",("s210","s810")),
)
def run(source:Path,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    images=[]
    for phase,family,levels in CASES:
        for op in OPS:
            for level in levels:
                stem="__".join((phase,family,op,level))
                path=source/(stem+".glb")
                meta=json.loads((source/(stem+".json")).read_text())
                meshes,digest=load_meshes(path)
                if meta.get("source_glb_sha256")!=digest:
                    raise ValueError("Unverified preview input: "+stem)
                for view in ("side","front_three_quarter"):
                    for mode in ("clay","wire"):
                        file=out/(stem+"__"+view+"__"+mode+".png")
                        render(meshes,view,mode,
                               stem+" | "+view+" | "+mode,file)
                        images.append({"png":file.name,
                                       "source_sha256":digest,
                                       "png_sha256":hashlib.sha256(
                                           file.read_bytes()).hexdigest()})
    result={"schema":"assetwright-advanced-geometry-review-v1",
            "artwork_role":"CPU diagnostic only; no automatic visual approval",
            "render_count":len(images),"files":images}
    if len(images)!=72:
        raise ValueError("Incomplete multiview development review")
    (out/"review_manifest.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Source verified advanced-form clay/wire previews:",len(images))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.source,a.out)

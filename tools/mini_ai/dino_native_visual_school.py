"""Render and teach from ONLY original source-hashed AssetWright native GLBs.

Images are input observations. DINOv2 Small is frozen, CPU-only and NEVER
builds meshes. The original Kotlin native mesh is the sole shape ground truth.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from advanced_form_student import OPERATIONS
from generated_glb_critic import inspect
from render_native_rocker_v2 import load_meshes, render

SOURCE_SCHEMA="assetwright-dino-native-school-v1"
MANIFEST_SCHEMA="assetwright-dino-native-observations-v1"
TEACHER_SCHEMA="assetwright-dino-native-teacher-v1"
MODEL="facebook/dinov2-small"
VIEWS=("side","front_three_quarter")
LEVELS={"train":(.12,.30,.50,.70,.90),
        "development":(.22,.46,.78),
        "validation":(.19,.56,.84)}
FAMILIES={"train":tuple("dntrain%02d"%n for n in range(1,7)),
          "development":("dndev01","dndev02"),
          "validation":("dnblind01","dnblind02")}


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_stems()->dict[str,tuple[str,str,str,float]]:
    result={}
    for split,families in FAMILIES.items():
        for family in families:
            for op in OPERATIONS:
                for strength in LEVELS[split]:
                    key="__".join((split,family,op.lower(),"s%03d"%round(strength*1000)))
                    result[key]=(split,family,op,strength)
    if len(result)!=252:
        raise AssertionError("Invalid frozen source sample count")
    return result


def read_source(source:Path,stem:str,expected:tuple)->dict:
    path=source/(stem+".glb")
    meta=json.loads((source/(stem+".json")).read_text())
    split,family,op,strength=expected
    if (meta.get("schema")!=SOURCE_SCHEMA or
            meta.get("native_generator")!="AssetWright-AdvancedFormLab" or
            (meta.get("case"),meta.get("split"),meta.get("family"),meta.get("operation"))!=
            (stem,split,family,op) or
            type(meta.get("strength")) not in (float,int) or
            abs(meta["strength"]-strength)>1e-5):
        raise ValueError("Invalid original native geometry identity: "+stem)
    if any(type(meta.get(k)) not in (float,int) or not .5<=meta[k]<=12
           for k in ("length","width","height")):
        raise ValueError("Invalid native source bounds")
    digest=sha(path)
    if meta.get("source_glb_sha256")!=digest:
        raise ValueError("Unverified native GLB hash")
    audit=inspect(path)
    if not (audit["model_sha256"]==digest and audit["mesh_parts"]==1 and
            900<=audit["triangles"]<=3000 and audit["invalid_triangles"]==0 and
            audit["boundary_edges"]==0 and audit["nonmanifold_edges"]==0 and
            audit["inverted_closed_parts"]==0 and audit["parts"][0]["signed_volume"]>0):
        raise ValueError("Unacceptable original GLB topology")
    return {"case":stem,"split":split,"family":family,"operation":op,
            "strength":strength,"length":meta["length"],"width":meta["width"],
            "height":meta["height"],"source_glb_sha256":digest,
            "triangle_count":audit["triangles"]}


def render_school(source:Path,images:Path,out:Path)->dict:
    from PIL import Image
    expected=expected_stems()
    glbs={p.stem for p in source.glob("*.glb")}
    metadata={p.stem for p in source.glob("*.json")}
    if glbs!=set(expected) or metadata!=set(expected):
        raise ValueError("Missing or extraneous original native GLB source cases")
    images.mkdir(parents=True,exist_ok=True)
    records=[]
    for stem,identity in sorted(expected.items()):
        record=read_source(source,stem,identity)
        meshes,digest=load_meshes(source/(stem+".glb"))
        if digest!=record["source_glb_sha256"]:
            raise ValueError("Mismatched source mesh")
        names={};hashes={}
        for view in VIEWS:
            path=images/(stem+"__"+view+".png")
            # Same label-free orthographic clay shader across all native forms.
            render(meshes,view,"clay","",path)
            with Image.open(path) as original:
                crop=original.convert("RGB").crop((74,85,976,658))
                crop.resize((224,224),Image.Resampling.BICUBIC).save(path)
            names[view]=path.name
            hashes[view]=sha(path)
        record["view_files"],record["view_sha256"]=names,hashes
        records.append(record)
    result={"schema":MANIFEST_SCHEMA,
            "native_generator":"AssetWright-AdvancedFormLab",
            "teacher":"frozen "+MODEL,"views":list(VIEWS),
            "records":records,"source_count":len(records),
            "source_hashed":True,"external_mesh_used":False,
            "note":"Image previews contain no operation/strength title text."}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"audited_source_glbs":len(records),
                      "label_free_original_camera_views":2*len(records)}))
    return result


def checked_manifest(manifest:dict,images:Path)->list[dict]:
    if (manifest.get("schema")!=MANIFEST_SCHEMA or
            manifest.get("native_generator")!="AssetWright-AdvancedFormLab" or
            manifest.get("views")!=list(VIEWS) or
            manifest.get("source_count")!=252):
        raise ValueError("Untrusted native school image manifest")
    expected=expected_stems()
    rows=manifest.get("records")
    if not isinstance(rows,list) or len(rows)!=len(expected):
        raise ValueError("Incomplete native visual curriculum")
    observed=set();hashes=set()
    for row in rows:
        stem=row.get("case")
        if stem not in expected or stem in observed:
            raise ValueError("Duplicated/unknown native source")
        split,family,op,strength=expected[stem]
        if ((row.get("split"),row.get("family"),row.get("operation"))!=
            (split,family,op) or abs(row.get("strength",-1)-strength)>1e-5):
            raise ValueError("Incorrect source construction labels")
        sha_glb=row.get("source_glb_sha256")
        if not isinstance(sha_glb,str) or not re.fullmatch(r"[0-9a-f]{64}",sha_glb) or sha_glb in hashes:
            raise ValueError("Repeated or invalid GLB source")
        names=row.get("view_files")
        checksums=row.get("view_sha256")
        if not isinstance(names,dict) or not isinstance(checksums,dict) or set(names)!=set(VIEWS) or set(checksums)!=set(VIEWS):
            raise ValueError("Incomplete source-hash-aligned camera views")
        for view in VIEWS:
            name=names[view]
            if not isinstance(name,str) or name!=stem+"__"+view+".png":
                raise ValueError("Untrusted source image path")
            path=images/name
            if not path.is_file() or sha(path)!=checksums[view]:
                raise ValueError("Tampered or missing original camera view")
        observed.add(stem)
        hashes.add(sha_glb)
    if observed!=set(expected):
        raise ValueError("Missing verified native samples")
    return rows


def teach_school(manifest_file:Path,images:Path,out:Path)->dict:
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor,Dinov2Model
    manifest=json.loads(manifest_file.read_text())
    rows=checked_manifest(manifest,images)
    torch.set_num_threads(min(2,torch.get_num_threads()))
    processor=AutoImageProcessor.from_pretrained(MODEL,trust_remote_code=False,use_fast=False)
    encoder=Dinov2Model.from_pretrained(MODEL,trust_remote_code=False,use_safetensors=True).eval().to("cpu")
    examples=[]
    for row in rows:
        batch=[]
        for view in VIEWS:
            with Image.open(images/row["view_files"][view]) as img:
                batch.append(img.convert("RGB"))
        with torch.inference_mode():
            vectors=encoder(**processor(images=batch,return_tensors="pt")).last_hidden_state[:,0,:].cpu().tolist()
        if len(vectors)!=2 or any(len(vec)!=384 for vec in vectors):
            raise ValueError("Invalid frozen DINOv2 representation")
        mean=[(vectors[0][i]+vectors[1][i])/2 for i in range(384)]
        examples.append({"case":row["case"],"source_glb_sha256":row["source_glb_sha256"],
                         "view_sha256":row["view_sha256"],
                         "frozen_visual_embedding":[round(float(v),8) for v in mean]})
    output={"schema":TEACHER_SCHEMA,"teacher":MODEL,"frozen":True,
            "external_mesh_generator":False,"examples":examples}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(output,separators=(",",":"))+"\n")
    print(json.dumps({"teacher":MODEL,"native_shapes_taught":len(examples),
                      "teacher_generates_geometry":False}))
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest="command",required=True)
    r=s.add_parser("render")
    r.add_argument("--source",type=Path,required=True)
    r.add_argument("--images",type=Path,required=True)
    r.add_argument("--out",type=Path,required=True)
    t=s.add_parser("teach")
    t.add_argument("--manifest",type=Path,required=True)
    t.add_argument("--images",type=Path,required=True)
    t.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if args.command=="render":
        render_school(args.source,args.images,args.out)
    else:
        teach_school(args.manifest,args.images,args.out)


if __name__=="__main__":
    main()

"""Original baseline-only 32x32 three-view shape identity dataset.

The old 16x16 before/after operation student is NEVER reinitialized.
The NEW independent identity pathway sees side, top and front views of
only the ORIGINAL undeformed shape. The same identity descriptor is
attached to ALL transform/strength examples from that family.

Identity renders use source-hashed original Kotlin GLBs, never correct
blind labels at inference. Old v6 replay only uses TRAINING families.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from dino_delta_school import hash_file
from render_native_rocker_v2 import load_meshes,render

SCHEMA="assetwright-original-three-view-shape-identity-v7"
SIDES=("side","front","top")
GRID=32
INPUT_DIM=3*GRID*GRID


def key_of(row):
    return row["split"]+"__"+row["family"]+"__baseline"


def generate(manifest_path:Path,source:Path,ordinary:Path,output:Path,
             *,allowed=("train","development","validation")):
    from PIL import Image

    manifest=json.loads(manifest_path.read_text())
    if (manifest.get("schema")!="assetwright-native-before-after-observations-v1"
        or manifest.get("study_id") not in ("multiform_v6","shape_identity_v7","form_fidelity_v8","identity_continuation_v9","geometry_mastery_v10","overnight_geometry_v11")
        or manifest.get("generator")!="AssetWright-Kotlin-AdvancedFormLab"
        or manifest.get("external_geometry_used") is not False):
        raise ValueError("Invalid source verified original form-identity study")
    output.mkdir(parents=True,exist_ok=True)
    families={}
    for row in manifest["records"]:
        if row["split"] not in allowed:
            continue
        stem=key_of(row)
        if stem in families:
            if (families[stem]["baseline_hash"]!=row["baseline_glb_sha256"]
                or families[stem]["archetype"]!=row["archetype"]):
                raise ValueError("Family identity changed across strengths")
            continue
        families[stem]={
            "archetype":row["archetype"],
            "baseline_hash":row["baseline_glb_sha256"],
            "split":row["split"],
            "family":row["family"],
            "segments":row["segments"],
            "stations":row["stations"]
        }
    index={}
    for stem,entry in sorted(families.items()):
        src=source/(stem+".glb")
        if hash_file(src)!=entry["baseline_hash"]:
            raise ValueError("Original baseline GLB changed")
        meshes,digest=load_meshes(src)
        if digest!=entry["baseline_hash"]:
            raise ValueError("Renderer original source GLB mismatch")
        links={}
        for view in SIDES:
            if view=="side":
                image=ordinary/(stem+"__side.png")
                if not image.exists():
                    raise ValueError("Missing matched source side view")
            else:
                image=output/(stem+"__"+view+".png")
                render(meshes,view,"clay","",image,fit_meshes=meshes)
                with Image.open(image) as full:
                    full.convert("RGB").crop((74,85,976,658)).resize(
                        (224,224),Image.Resampling.BICUBIC).save(image)
            links[view]={
                "path":image.name,
                "sha256":hash_file(image)
            }
        index[stem]={**entry,"views":links}
    record={
        "schema":SCHEMA,
        "study_id":manifest["study_id"],
        "source_count":len(families),
        "splits":list(allowed),
        "no_blind_ground_truth_as_neural_input":True,
        "input_only_original_baseline":True,
        "original_glb_source_SHA_enforced":True,
        "family_index":index
    }
    (output/"index.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({
        "schema":SCHEMA,"study":manifest["study_id"],
        "original_shaped_baselines":len(index),
        "new_original_front_top_renders":2*len(index)
    }),flush=True)
    return record


def features(row,ordinary:Path,extra:Path,index:dict):
    """Identity features contain no action label, strength or changed mesh."""
    from PIL import Image
    import numpy as np

    stem=key_of(row)
    entry=index["family_index"].get(stem)
    if (index.get("schema")!=SCHEMA or entry is None
        or entry["baseline_hash"]!=row["baseline_glb_sha256"]):
        raise ValueError("Three-view original source identity is not verified")
    output=[]
    for view in SIDES:
        info=entry["views"][view]
        path=(ordinary if view=="side" else extra)/info["path"]
        if hash_file(path)!=info["sha256"]:
            raise ValueError("Source baseline silhouette image hash mismatch")
        with Image.open(path) as original:
            image=np.asarray(original.convert("RGB").resize(
                (GRID,GRID),Image.Resampling.BOX),dtype=np.float32)/255
        grey=.299*image[:,:,0]+.587*image[:,:,1]+.114*image[:,:,2]
        mask=np.clip((grey-.10)*3.2,0,1)
        output.extend(mask.ravel().tolist())
    if len(output)!=INPUT_DIM:
        raise ValueError("3-view shape identity descriptor incomplete")
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("manifest","source","images","out"):
        p.add_argument("--"+field,type=Path,required=True)
    p.add_argument("--train-only",action="store_true")
    a=p.parse_args()
    allowed=("train",) if a.train_only else (
        "train","development","validation")
    generate(a.manifest,a.source,a.images,a.out,allowed=allowed)


if __name__=="__main__":
    main()

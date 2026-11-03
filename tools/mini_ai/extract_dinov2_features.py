"""Frozen DINOv2 image feature extraction for original AssetWright meshes.

This script uses a pretrained vision encoder ONLY for supervised features.
It cannot generate, export, or import third-party 3D meshes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

MODEL_ID="facebook/dinov2-small"
SCHEMA="assetwright-frozen-dinov2-features-v1"

def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def extract(manifest_file:Path,image_dir:Path,destination:Path)->dict:
    from PIL import Image
    import torch
    from transformers import AutoImageProcessor,Dinov2Model
    from visual_transfer_student import MANIFEST,valid_sha
    manifest=json.loads(manifest_file.read_text())
    if manifest.get("schema")!=MANIFEST:
        raise ValueError("Unexpected render manifest")
    processor=AutoImageProcessor.from_pretrained(MODEL_ID,trust_remote_code=False)
    model=Dinov2Model.from_pretrained(MODEL_ID,trust_remote_code=False,use_safetensors=True)
    model.eval().to("cpu")
    torch.set_num_threads(min(2,torch.get_num_threads()))
    rows=[]
    for example in manifest.get("examples",[]):
        if not example.get("original_procedural_asset") or not valid_sha(example.get("source_glb_sha256")):
            raise ValueError("External meshes not accepted as own-generator training")
        images=[]
        for view in ("front","side","top","three_quarter"):
            filename=example.get("view_files",{}).get(view)
            if not isinstance(filename,str) or Path(filename).name!=filename or not filename.endswith(".png"):
                raise ValueError("Unsafe or missing render path")
            path=image_dir/filename
            if digest(path)!=example["view_sha256"][view]:
                raise ValueError("Rendered view was altered")
            with Image.open(path) as image:
                images.append(image.convert("RGB"))
        inputs=processor(images=images,return_tensors="pt")
        with torch.inference_mode():
            vectors=model(**inputs).last_hidden_state[:,0,:].cpu().tolist()
        mean=[sum(row[i] for row in vectors)/len(vectors) for i in range(384)]
        rows.append({"sample_id":example["sample_id"],
                     "source_glb_sha256":example["source_glb_sha256"],
                     "view_sha256":example["view_sha256"],
                     "embedding":[round(x,8) for x in mean]})
    result={"schema":SCHEMA,"model_id":MODEL_ID,"teacher_is_frozen":True,
            "source":"only original AssetWright four-view renderings",
            "teacher_produces_meshes":False,"features":rows}
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,separators=(",",":"))+"\n")
    print("ASSETWRIGHT_FROZEN_FEATURES_CREATED",len(rows))
    return result

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--images",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    extract(args.manifest,args.images,args.out)

if __name__=="__main__":
    main()

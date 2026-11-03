"""Frozen DINOv2-small features for licensed Zero-to-CAD reference *images*.

No CadQuery execution, third-party model generation, or Android deployment.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

MODEL="facebook/dinov2-small"
SCHEMA="assetwright-zero-to-cad-frozen-dinov2-v1"

def image_candidates(manifest:dict,image_dir:Path):
    if manifest.get("schema")!="assetwright-zero-to-cad-operations-v1" or manifest.get("license")!="Apache-2.0":
        raise ValueError("Unapproved source manifest")
    for row in manifest.get("records",[]):
        names=row.get("view_files",{})
        hashes=row.get("view_sha256",{})
        if not isinstance(names,dict) or not isinstance(hashes,dict): continue
        verified=[]
        for key in ("image_0","image_4"):
            name=names.get(key)
            if not isinstance(name,str) or Path(name).name!=name or not name.endswith(".png"):
                continue
            path=image_dir/name
            if hashlib.sha256(path.read_bytes()).hexdigest()!=hashes.get(key):
                raise ValueError("Image changed since source ingestion")
            verified.append(path)
        if verified: yield row,verified

def extract(manifest_file:Path,images:Path,out:Path)->dict:
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor,Dinov2Model
    manifest=json.loads(manifest_file.read_text())
    pairs=list(image_candidates(manifest,images))
    if not pairs: raise ValueError("No verified CAD views for frozen visual teacher")
    processor=AutoImageProcessor.from_pretrained(MODEL,trust_remote_code=False)
    encoder=Dinov2Model.from_pretrained(MODEL,trust_remote_code=False,use_safetensors=True)
    encoder.eval().to("cpu")
    torch.set_num_threads(min(2,torch.get_num_threads()))
    records=[]
    for row,files in pairs:
        views=[]
        for file in files:
            with Image.open(file) as image:
                views.append(image.convert("RGB"))
        inputs=processor(images=views,return_tensors="pt")
        with torch.inference_mode():
            embedding=encoder(**inputs).last_hidden_state[:,0,:].mean(dim=0).cpu().tolist()
        if len(embedding)!=384: raise ValueError("Unexpected teacher feature count")
        records.append({"source_id":row["source_id"],"code_sha256":row["code_sha256"],
                        "split":row["split"],"view_sha256":row["view_sha256"],
                        "frozen_visual_embedding":[round(float(x),8) for x in embedding]})
    result={"schema":SCHEMA,"model_id":MODEL,"teacher_frozen":True,
            "teacher_generates_3d":False,"source_dataset":manifest["dataset"],
            "source_split":manifest["split"],"source_license":manifest["license"],
            "records":records}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,separators=(",",":"))+"\n")
    print(json.dumps({"model":MODEL,"features":len(records),
                      "model_generator":"AssetWright only"}))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--images",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    extract(a.manifest,a.images,a.out)
if __name__=="__main__": main()

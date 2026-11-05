"""Source-audited paired native GLBs, fixed-camera image differences, DINO teacher.

Original Kotlin AdvancedFormLab is the ONLY builder. The frozen vision model
observes before/after renders as an auxiliary teacher; never generates meshes.
"""
from __future__ import annotations
import argparse
from itertools import product
import hashlib
import json
import math
import os
from pathlib import Path
import re

from advanced_form_student import OPERATIONS,features_from_glb
from generated_glb_critic import inspect,_read_glb,_accessor
from render_native_rocker_v2 import load_meshes,render
from visual_transfer_student import project_teacher

SOURCE="assetwright-native-before-after-source-v1"
MANIFEST="assetwright-native-before-after-observations-v1"
TEACHER="assetwright-native-before-after-dinov2-v1"
DINO="facebook/dinov2-small"
VIEWS=("side","front_three_quarter")
FAMILIES={
    "train":tuple("bdtrain%02d"%i for i in range(1,13)),
    "development":("bddev01","bddev02","bddev03"),
    "validation":("bdhold01","bdhold02","bdhold03")
}
LEVELS={
    "train":(.12,.28,.44,.62,.82),
    "development":(.20,.49,.76),
    "validation":(.15,.54,.89)
}
# An explicit study switch keeps historical outcomes exactly reproducible.
# bdhold01..03 are already inspected and NEVER become fresh validation again.
STUDY=os.environ.get("ASSETWRIGHT_DINO_STUDY","delta_v1")
if STUDY=="strength_v2":
    FAMILIES={
        "train":tuple("bs_train%02d"%i for i in range(1,19)),
        "development":tuple("bs_dev%02d"%i for i in range(1,5)),
        "validation":tuple("bs_blind%02d"%i for i in range(1,5))
    }
    LEVELS={
        "train":(.04,.16,.32,.48,.64,.80,.96),
        "development":(.11,.39,.71,.91),
        "validation":(.09,.43,.67,.93)
    }
elif STUDY!="delta_v1":
    raise ValueError("Unapproved native source curriculum")
EXPECTED=sum(len(FAMILIES[phase])*6*len(LEVELS[phase])
             for phase in FAMILIES)
BASELINES=sum(len(x) for x in FAMILIES.values())


def hash_file(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_changes():
    rows={}
    for split,families in FAMILIES.items():
        for family in families:
            for op in OPERATIONS:
                for level in LEVELS[split]:
                    stem="__".join((split,family,op.lower(),"s%03d"%round(1000*level)))
                    base="__".join((split,family,"baseline"))
                    rows[stem]=(split,family,op,level,base)
    if len(rows)!=EXPECTED: raise AssertionError("Unexpected protected source split")
    return rows


def read_case(root:Path,stem:str,expected:tuple,*,baseline:bool=False)->dict:
    split,family,op,strength=expected
    path=root/(stem+".glb")
    meta=json.loads((root/(stem+".json")).read_text())
    if not (meta.get("schema")==SOURCE
        and meta.get("original_engine")=="AssetWright-AdvancedFormLab"
        and (meta.get("case"),meta.get("split"),meta.get("family"),meta.get("operation"))==
            (stem,split,family,op)
        and meta.get("baseline") is baseline
        and type(meta.get("strength")) in (float,int)
        and abs(meta["strength"]-strength)<1e-5):
        raise ValueError("Invalid original Kotlin before/after provenance: "+stem)
    if any(type(meta.get(name)) not in (float,int)
           or not math.isfinite(meta[name])
           or not .5<=meta[name]<=12 for name in ("length","width","height")):
        raise ValueError("Invalid physical original dimensions")
    digest=hash_file(path)
    if meta.get("source_glb_sha256")!=digest:
        raise ValueError("Source Kotlin GLB hash tampering")
    audit=inspect(path)
    if not (audit["model_sha256"]==digest and audit["mesh_parts"]==1
        and 900<=audit["triangles"]<=3000 and audit["invalid_triangles"]==0
        and audit["boundary_edges"]==0 and audit["nonmanifold_edges"]==0
        and audit["inverted_closed_parts"]==0
        and audit["parts"][0]["signed_volume"]>0):
        raise ValueError("Source Kotlin GLB fails topology gate")
    return {"source_sha256":digest,"meta":meta,"audit":audit}


def native_delta(before:Path,after:Path)->tuple[list[float],float]:
    a,_=features_from_glb(before,24,24)
    b,_=features_from_glb(after,24,24)
    delta=[bb-aa for aa,bb in zip(a,b)]
    adoc,abuf,_=_read_glb(before)
    bdoc,bbuf,_=_read_glb(after)
    pa=adoc["meshes"][0]["primitives"][0]
    pb=bdoc["meshes"][0]["primitives"][0]
    va=_accessor(adoc,abuf,pa["attributes"]["POSITION"],"positions")
    vb=_accessor(bdoc,bbuf,pb["attributes"]["POSITION"],"positions")
    if len(va)!=len(vb) or len(va)!=602:
        raise ValueError("Native geometry lost true corresponding source vertices")
    displacement=math.sqrt(sum(
        sum((x-y)**2 for x,y in zip(aa,bb)) for aa,bb in zip(va,vb))/
        (3*len(va)))
    if any(not math.isfinite(v) or abs(v)>3 for v in delta) or displacement<=1.e-5:
        raise ValueError("Missing physically measurable native transformation")
    return delta,displacement


def framing_bounds(parts:list[dict]):
    mins=[min(p["min"][i] for p in parts) for i in range(3)]
    maxs=[max(p["max"][i] for p in parts) for i in range(3)]
    corners=[tuple(q) for q in product(*zip(mins,maxs))]
    return [("shared-camera-framing",corners,[],(255,255,255))]


def render_school(source:Path,images:Path,manifest_path:Path)->dict:
    from PIL import Image
    expected=expected_changes()
    bases={stem for _,_,_,_,stem in expected.values()}
    glbs={p.stem for p in source.glob("*.glb")}
    docs={p.stem for p in source.glob("*.json")}
    if glbs!=set(expected)|bases or docs!=glbs or len(glbs)!=EXPECTED+BASELINES:
        raise ValueError("Incomplete or contaminated original paired GLB source school")
    audited={}
    for stem,identity in expected.items():
        audited[stem]=read_case(source,stem,identity[:4],baseline=False)
    for stem in bases:
        split,family,_=stem.split("__")
        audited[stem]=read_case(source,stem,(split,family,"BASELINE",0.),baseline=True)
    for stem,(split,family,_,_,base) in expected.items():
        dims=audited[stem]["meta"]
        baseline=audited[base]["meta"]
        if any(abs(dims[k]-baseline[k])>1.e-6 for k in ("length","width","height")):
            raise ValueError("Changed dimensions, not a controlled operation delta")
    frame={}
    for split,families in FAMILIES.items():
        for family in families:
            stems=[x for x in glbs if x.startswith(split+"__"+family+"__")]
            frame[(split,family)]=framing_bounds(
                [audited[stem]["audit"]["parts"][0] for stem in stems])
    images.mkdir(parents=True,exist_ok=True)
    view_files={}
    for stem in sorted(glbs):
        if stem in bases:
            split,family,_=stem.split("__")
            view_role="before"
        else:
            split,family,*_=stem.split("__")
            view_role="after"
        meshes,digest=load_meshes(source/(stem+".glb"))
        if digest!=audited[stem]["source_sha256"]:
            raise ValueError("Image source GLB digest mismatch")
        names={};hashes={}
        for view in VIEWS:
            path=images/(stem+"__"+view+".png")
            # Every source in the SAME family shares one exact orthographic camera.
            render(meshes,view,"clay","",path,fit_meshes=frame[(split,family)])
            with Image.open(path) as original:
                original.convert("RGB").crop((74,85,976,658)).resize(
                    (224,224),Image.Resampling.BICUBIC).save(path)
            names[view]=path.name
            hashes[view]=hash_file(path)
        view_files[stem]=(names,hashes)
    records=[]
    for stem,(split,family,op,strength,base) in sorted(expected.items()):
        source_data=audited[stem]
        delta,magnitude=native_delta(source/(base+".glb"),source/(stem+".glb"))
        before_names,before_hashes=view_files[base]
        after_names,after_hashes=view_files[stem]
        records.append({
            "case":stem,"split":split,"family":family,"operation":op,
            "strength":strength,
            "baseline_case":base,
            "baseline_glb_sha256":audited[base]["source_sha256"],
            "modified_glb_sha256":source_data["source_sha256"],
            "length":source_data["meta"]["length"],
            "width":source_data["meta"]["width"],
            "height":source_data["meta"]["height"],
            "before_view_files":before_names,"before_view_sha256":before_hashes,
            "after_view_files":after_names,"after_view_sha256":after_hashes,
            "measured_morphology_delta":delta,
            "measured_vertex_displacement":magnitude
        })
    manifest={
        "schema":MANIFEST,"generator":"AssetWright-Kotlin-AdvancedFormLab",
        "teacher":"frozen "+DINO,"views":list(VIEWS),"source_count":486,
        "paired_examples":len(records),"renderer":"fixed-family-orthographic-clay","study_id":STUDY,
        "no_text_labels_in_images":True,"external_geometry_used":False,
        "records":records
    }
    manifest_path.parent.mkdir(parents=True,exist_ok=True)
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"source_glbs":len(glbs),"before_after_pairs":len(records),
                      "original_fixed_camera_renders":2*len(glbs)}))
    return manifest


def checked_manifest(manifest:dict,images:Path)->list[dict]:
    if (manifest.get("schema")!=MANIFEST or
        manifest.get("generator")!="AssetWright-Kotlin-AdvancedFormLab" or
        manifest.get("views")!=list(VIEWS) or
        manifest.get("paired_examples")!=EXPECTED or
        manifest.get("source_count")!=EXPECTED+BASELINES or
        manifest.get("renderer")!="fixed-family-orthographic-clay" or
        manifest.get("study_id")!=STUDY or
        manifest.get("external_geometry_used") is not False):
        raise ValueError("Unknown native delta school source")
    expected=expected_changes()
    records=manifest.get("records")
    if not isinstance(records,list) or len(records)!=EXPECTED:
        raise ValueError("Incomplete original before/after records")
    seen=set();modified_hashes=set();base_by_family={}
    for item in records:
        case=item.get("case")
        if case in seen or case not in expected:
            raise ValueError("Duplicate or unexpected native transformation case")
        split,family,op,strength,base=expected[case]
        if (item.get("split"),item.get("family"),item.get("operation"),
            item.get("baseline_case"))!=(split,family,op,base):
            raise ValueError("Native pair construction/source identity mismatch")
        if type(item.get("strength")) not in (float,int) or abs(item["strength"]-strength)>1e-5:
            raise ValueError("Incorrect native supervision strength")
        baseline_hash=item.get("baseline_glb_sha256")
        source_hash=item.get("modified_glb_sha256")
        if (not isinstance(source_hash,str) or not re.fullmatch(r"[0-9a-f]{64}",source_hash)
            or source_hash in modified_hashes or not isinstance(baseline_hash,str)
            or not re.fullmatch(r"[0-9a-f]{64}",baseline_hash)
            or source_hash==baseline_hash):
            raise ValueError("Missing, repeated or tampered original native mesh hash")
        family_key=(split,family)
        if family_key in base_by_family and base_by_family[family_key]!=baseline_hash:
            raise ValueError("Different original baselines within same source family")
        base_by_family[family_key]=baseline_hash
        delta=item.get("measured_morphology_delta")
        if not isinstance(delta,list) or len(delta)!=6 or any(
            type(v) not in (float,int) or not math.isfinite(v) or abs(v)>3 for v in delta):
            raise ValueError("Unverified physical shape-change descriptors")
        for role,stem in (("before",base),("after",case)):
            names=item.get(role+"_view_files")
            hashes=item.get(role+"_view_sha256")
            if not isinstance(names,dict) or not isinstance(hashes,dict) or set(names)!=set(VIEWS) or set(hashes)!=set(VIEWS):
                raise ValueError("Incomplete fixed-camera images for native delta")
            for view in VIEWS:
                path=images/(stem+"__"+view+".png")
                if names[view]!=path.name or not path.is_file() or hash_file(path)!=hashes[view]:
                    raise ValueError("Tampered before/after original image")
        modified_hashes.add(source_hash)
        seen.add(case)
    if seen!=set(expected) or len(base_by_family)!=BASELINES:
        raise ValueError("Missing disjoint original source families")
    return records


def teach(manifest_path:Path,images:Path,out:Path)->dict:
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor,Dinov2Model
    manifest=json.loads(manifest_path.read_text())
    rows=checked_manifest(manifest,images)
    torch.set_num_threads(min(2,torch.get_num_threads()))
    processor=AutoImageProcessor.from_pretrained(DINO,trust_remote_code=False,use_fast=False)
    encoder=Dinov2Model.from_pretrained(DINO,trust_remote_code=False,use_safetensors=True).eval().to("cpu")
    cache={}
    def embed(paths:list[Path]):
        key=tuple(str(x) for x in paths)
        if key not in cache:
            views=[]
            for path in paths:
                with Image.open(path) as image:
                    views.append(image.convert("RGB"))
            with torch.inference_mode():
                vectors=encoder(**processor(images=views,return_tensors="pt")).last_hidden_state[:,0,:].cpu().tolist()
            if len(vectors)!=2 or any(len(v)!=384 for v in vectors):
                raise ValueError("Unapproved frozen-DINO feature dimension")
            cache[key]=[sum(v[i] for v in vectors)/len(vectors) for i in range(384)]
        return cache[key]
    lessons=[]
    for row in rows:
        before=embed([images/row["before_view_files"][v] for v in VIEWS])
        after=embed([images/row["after_view_files"][v] for v in VIEWS])
        a=project_teacher(before)
        b=project_teacher(after)
        signature=[round(y-x,8) for x,y in zip(a,b)]
        lessons.append({
            "case":row["case"],"baseline_glb_sha256":row["baseline_glb_sha256"],
            "modified_glb_sha256":row["modified_glb_sha256"],
            "before_view_sha256":row["before_view_sha256"],
            "after_view_sha256":row["after_view_sha256"],
            "frozen_dino_delta_signature":signature
        })
    package={"schema":TEACHER,"teacher":DINO,"teacher_frozen":True,
             "teacher_generates_3d":False,"examples":lessons}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(package,separators=(",",":"))+"\n")
    print(json.dumps({"original_shape_changes_taught":len(lessons),
                      "image_groups_encoded":len(cache),"teacher":DINO}))
    return package


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
    a=p.parse_args()
    if a.command=="render":render_school(a.source,a.images,a.out)
    else:teach(a.manifest,a.images,a.out)


if __name__=="__main__":
    main()

"""Shape-family independent 64-point native displacement supervision.

Variable original mesh tessellation is allowed: sample vertices at the same
normalized longitudinal/circumference fractions across 24, 32, and 40 sides.
GLB source SHA256 and family identity are mandatory. No blind target data
is ever read by this training-only module.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path

from generated_glb_critic import _accessor,_read_glb
from advanced_form_student import OPERATIONS

POINT_COUNT=64
FIELD_SIZE=192


def sampled(file:Path,sha:str,segments:int,stations:int):
    raw=file.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=sha:
        raise ValueError("Original native training GLB no longer matches source SHA")
    doc,binary,_=_read_glb(file)
    if len(doc.get("meshes",[]))!=1:
        raise ValueError("Training only owns one closed original source mesh")
    primitives=doc["meshes"][0]["primitives"]
    if len(primitives)!=1:
        raise ValueError("Original native source topology unexpectedly changed")
    coords=_accessor(doc,binary,
        primitives[0]["attributes"]["POSITION"],"positions")
    if len(coords)!=(stations+1)*segments+2:
        raise ValueError("Source-form topology cannot be reconstructed by normalized rings")
    points=[]
    for r in range(1,9):
        station=round(r*stations/9)
        for a in range(8):
            side=round(a*segments/8)%segments
            points.extend(coords[station*segments+side])
    if len(points)!=FIELD_SIZE or not all(math.isfinite(x) for x in points):
        raise ValueError("Invalid original source vertex supervision")
    return points


def prepare(rows:list,source:Path):
    import numpy as np
    if not rows or any(item["split"] not in ("train","development") for item in rows):
        raise ValueError("Cannot open unused blind source geometry for optimizer")
    families={}
    for row in rows:
        if row.get("form") not in (
            "SPINDLE","WEDGE","BOX_MODULE","BARREL",
            "ARCH","BLADE","CANOPY_POD","TRUSS_BEAM"):
            raise ValueError("Missing original form identity supervision")
        if row.get("segments") not in (24,32,40) or row.get("stations") not in (24,32):
            raise ValueError("Invalid native topology source")
        families.setdefault((row["split"],row["family"]),[]).append(row)
    baselines={}
    fields={}
    for key,items in families.items():
        first=items[0]
        if any(x["form"]!=first["form"] or
               x["segments"]!=first["segments"] or
               x["stations"]!=first["stations"] or
               x["dims"]!=first["dims"] or
               x["baseline_hash"]!=first["baseline_hash"] for x in items):
            raise ValueError("Family changes form, topology or source dimensions")
        split,family=key
        before=sampled(source/(split+"__"+family+"__baseline.glb"),
            first["baseline_hash"],first["segments"],first["stations"])
        baselines[key]=before
        scale=max(first["dims"].values())
        for op in OPERATIONS:
            group=[r for r in items if r["op"]==op]
            if len(group)<3 or len({x["strength"] for x in group})!=len(group):
                raise ValueError("Missing original native multi-form control sweep")
            biggest=max(group,key=lambda x:x["strength"])
            final=sampled(source/(biggest["case"]+".glb"),
                biggest["source_hash"],first["segments"],first["stations"])
            displacements=[(a-b)/(biggest["strength"]*scale)
                           for a,b in zip(final,before)]
            if sum(abs(z) for z in displacements)<1.e-5:
                raise ValueError("No measurable shape-specific native operator")
            fields[(key,op)]=displacements
    basis=[]
    targets=[]
    digests=[]
    for item in rows:
        key=(item["split"],item["family"])
        actual=sampled(source/(item["case"]+".glb"),
            item["source_hash"],item["segments"],item["stations"])
        original=baselines[key]
        factor=max(item["dims"].values())
        targets.append([(a-b)/factor for a,b in zip(actual,original)])
        basis.append([fields[(key,op)] for op in OPERATIONS])
        digests.append(item["source_hash"])
    bases=np.asarray(basis,dtype=np.float32)
    truth=np.asarray(targets,dtype=np.float32)
    if bases.shape!=(len(rows),6,FIELD_SIZE) or truth.shape!=(len(rows),FIELD_SIZE):
        raise ValueError("Source-matched normalized vertex proxy incomplete")
    if not np.isfinite(bases).all() or not np.isfinite(truth).all():
        raise ValueError("Original geometry proxy contains unbounded 3D fields")
    return {
        "basis":bases,"targets":truth,
        "count":len(rows),"sampled_points":POINT_COUNT,
        "source_sha256":hashlib.sha256(
            "\n".join(sorted(digests)).encode()).hexdigest()
    }


def proxy_loss(operation_logits,heads,form_logits,operation_ids,
               form_ids,basis,targets):
    import torch
    import torch.nn.functional as F
    if (operation_logits.shape[1]!=6 or
        heads.shape!=operation_logits.shape or
        form_logits.shape[1]!=9 or
        basis.shape!=(len(operation_ids),6,FIELD_SIZE) or
        targets.shape!=(len(operation_ids),FIELD_SIZE)):
        raise ValueError("Differentiable native geometry loss shape mismatch")
    probabilities=operation_logits.softmax(dim=1)
    displacement=(
        probabilities[:,:,None]*heads[:,:,None]*basis).sum(dim=1)
    chosen=heads.gather(1,operation_ids[:,None]).flatten()
    matching=basis[torch.arange(len(chosen)),operation_ids,:]*chosen[:,None]
    # Learn the REAL native surface plus correct shape archetype.
    return (
        22*F.smooth_l1_loss(displacement,targets,beta=.007)
        +10*F.smooth_l1_loss(matching,targets,beta=.007)
        +.45*F.cross_entropy(form_logits,form_ids)
    )

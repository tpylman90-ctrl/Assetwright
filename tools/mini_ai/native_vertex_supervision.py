"""Physically grounded, differentiable supervision from ORIGINAL Kotlin GLBs.

Never accepts a teacher-produced mesh or uses hidden heldout vertex targets
as neural inputs. Paired source and baseline share exact ordered positions.
Each source-family native operation contributes an approximate differentiable
vertex deformation basis. Final validation ALWAYS executes the original
Kotlin AdvancedFormLab to check the true 3D result, not the surrogate.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

from advanced_form_student import OPERATIONS
from generated_glb_critic import _read_glb,_accessor

SAMPLE_RINGS=(1,4,7,10,13,16,19,23)
SAMPLE_EDGES=(0,3,6,9,12,15,18,21)
VERTEX_IDS=tuple(r*24+a for r in SAMPLE_RINGS for a in SAMPLE_EDGES)
SAMPLE_SIZE=len(VERTEX_IDS)*3
GENERATOR="AssetWright-AdvancedFormLab"


def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vertices(path:Path,expected_sha:str)->list[float]:
    if sha256(path)!=expected_sha:
        raise ValueError("Changed original source GLB SHA256")
    doc,blob,digest=_read_glb(path)
    meshes=doc.get("meshes")
    if not isinstance(meshes,list) or len(meshes)!=1:
        raise ValueError("Only original single-shell mesh can teach native differences")
    primitives=meshes[0].get("primitives")
    if not isinstance(primitives,list) or len(primitives)!=1:
        raise ValueError("Original topology unexpectedly split or replaced")
    positions=_accessor(doc,blob,primitives[0]["attributes"]["POSITION"],"positions")
    if len(positions)!=602:
        raise ValueError("Geometry teacher needs 602 exact corresponding Kotlin vertices")
    out=[v for i in VERTEX_IDS for v in positions[i]]
    if len(out)!=SAMPLE_SIZE or not all(math.isfinite(x) for x in out):
        raise ValueError("Invalid original 3D geometry")
    return out


def prepare(rows:list[dict],source:Path)->dict:
    """Read only training or development rows. Never call for blind cohort."""
    import numpy as np
    if not rows or any(x["split"] not in ("train","development") for x in rows):
        raise ValueError("Cannot extract leaked blind geometric target labels for training")
    by_family={}
    for row in rows:
        key=(row["split"],row["family"])
        by_family.setdefault(key,[]).append(row)
    baseline_cache={}
    unit_fields={}
    target_cache={}
    for key,items in by_family.items():
        if len(items)!=6*(len(items)//6) or len({x["op"] for x in items})!=6:
            raise ValueError("Missing native operation families")
        first=items[0]
        split,family=key
        baseline_case=f"{split}__{family}__baseline"
        baseline_path=source/(baseline_case+".glb")
        if not baseline_path.is_file():
            raise ValueError("Original baseline not found "+baseline_case)
        baseline=vertices(baseline_path,first["baseline_hash"])
        baseline_cache[key]=baseline
        dimensions=first["dims"]
        if any(x["dims"]!=dimensions or x["baseline_hash"]!=first["baseline_hash"]
               for x in items):
            raise ValueError("Native family changes dimensions or original baseline")
        for op in OPERATIONS:
            group=[x for x in items if x["op"]==op]
            strengths=[x["strength"] for x in group]
            if len(set(strengths))!=len(strengths) or any(
                not 0<value<=1 for value in strengths):
                raise ValueError("Missing a valid original native strength progression")
            largest=max(group,key=lambda x:x["strength"])
            shape=vertices(source/(largest["case"]+".glb"),largest["source_hash"])
            scale=max(dimensions.values())
            unit_fields[(key,op)]=[
                (a-b)/(scale*largest["strength"]) for a,b in zip(shape,baseline)]
            if sum(abs(x) for x in unit_fields[(key,op)])<1.e-5:
                raise ValueError("Original native operator has no actual 3D effect")
    basis=[];actual=[];identities=[]
    for row in rows:
        key=(row["split"],row["family"])
        original=vertices(source/(row["case"]+".glb"),row["source_hash"])
        baseline=baseline_cache[key]
        normalizer=max(row["dims"].values())
        expected=[(a-b)/normalizer for a,b in zip(original,baseline)]
        actual.append(expected)
        basis.append([unit_fields[(key,op)] for op in OPERATIONS])
        identities.append(row["source_hash"])
    B=np.asarray(basis,dtype=np.float32)
    Y=np.asarray(actual,dtype=np.float32)
    if B.shape!=(len(rows),6,SAMPLE_SIZE) or Y.shape!=(len(rows),SAMPLE_SIZE):
        raise ValueError("Indexed native geometry differs across original sources")
    if not np.isfinite(B).all() or not np.isfinite(Y).all():
        raise ValueError("Invalid original native vertex displacements")
    return {
        "basis":B,"targets":Y,
        "verified_train_GLBS":len(rows),
        "sampled_positions_per_mesh":len(VERTEX_IDS),
        "source_digests_sha256":hashlib.sha256(
            "\n".join(sorted(identities)).encode()).hexdigest(),
        "surrogate":"6 per-family original Kotlin op displacement bases",
        "geometry_is_label_only":True
    }


def proxy_loss(logits,heads,basis,targets,operator_ids,*,geometry_weight=1.0):
    """Backpropagate 3D vertex error into BOTH class and strength predictions."""
    import torch
    import torch.nn.functional as F
    if (logits.ndim!=2 or logits.shape[1]!=6
        or heads.shape!=logits.shape
        or basis.shape!=(logits.shape[0],6,SAMPLE_SIZE)
        or targets.shape!=(logits.shape[0],SAMPLE_SIZE)
        or operator_ids.shape!=(logits.shape[0],)):
        raise ValueError("Native supervised geometry shape mismatch")
    # Differentiable proxy: op-specific unit-strength displacements from
    # actual Kotlin GLBs, blended with soft classification probabilities.
    probabilities=torch.softmax(logits,dim=1)
    predicted=(probabilities[:,:,None]*heads[:,:,None]*basis).sum(dim=1)
    # Stronger physical displacement gets an actual supervised signal.
    # No canonical depth or copied teacher embeddings are required.
    mesh_error=F.smooth_l1_loss(predicted,targets,beta=.006)
    # Teacher-forced geometry term informs strength on the TRUE native op.
    idx=torch.arange(logits.shape[0],device=logits.device)
    operator_delta=heads[idx,operator_ids,None]*basis[idx,operator_ids]
    strength_geometry=F.smooth_l1_loss(operator_delta,targets,beta=.006)
    return geometry_weight*(24.*mesh_error+12.*strength_geometry)


def difficulty_scores(logits,heads,operations,strengths):
    """Original correct labels only, never self-label predicted mistakes."""
    import torch
    import torch.nn.functional as F
    if not (
        logits.ndim==2 and logits.shape[1]==6 and
        heads.shape==logits.shape and
        operations.shape==strengths.shape==(logits.shape[0],)):
        raise ValueError("Hardness must use supervised original native labels")
    idx=torch.arange(len(operations),device=logits.device)
    label_ce=F.cross_entropy(logits,operations,reduction="none")
    actual_strength=heads[idx,operations]
    absolute_strength=(actual_strength-strengths).abs()
    hard=label_ce+.65*absolute_strength*3.
    if not torch.isfinite(hard).all():
        raise ValueError("Unbounded observed real-labeled geometry mistake")
    return hard.detach()

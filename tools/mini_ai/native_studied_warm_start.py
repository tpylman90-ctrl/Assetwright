"""Re-use OWN original Mini AI weights without erasing accumulated knowledge.

The checkpoint is teacher-free, source-hashed, research-only. Future learning
can warm-start from it on NEW cohorts and test whether the old skills survive.
When image normalizers change, analytically rebase the first dense layer so
identical raw camera pixels give the SAME first pre-activation as before.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

SCHEMA="assetwright-permanent-original-mini-native-knowledge-v1"
NORM="assetwright-native-student-normalization-v1"
DEFAULT=Path("training/knowledge/native_strength_teacher_free_42080318206")


def load_provenance(folder:Path):
    lineage=json.loads((folder/"model_lineage.json").read_text())
    standard=json.loads((folder/"normalization.json").read_text())
    weight_file=folder/"owned_native_student.safetensors"
    if not (lineage.get("schema")==SCHEMA
            and lineage.get("condition")=="teacher_free"
            and lineage.get("teacher_used_for_student") is False
            and lineage.get("external_3d_generator_used") is False
            and lineage.get("approved_for_production") is False
            and lineage.get("android_installed") is False
            and lineage.get("original_source_GLBS_verified")==888
            and lineage.get("new_native_reconstructions_verified")==192
            and lineage.get("selected_seed")==2029
            and lineage.get("heldout_count")==96
            and standard.get("schema")==NORM
            and standard.get("input_feature_dim")==1536
            and standard.get("hidden_dim")==96
            and len(standard.get("supported_ops",[]))==6):
        raise ValueError("Unexpected or non-research-owned native student lineage")
    digest=hashlib.sha256(weight_file.read_bytes()).hexdigest()
    if digest!=lineage.get("saved_weights_sha256"):
        raise ValueError("Native student's permanent saved weights were modified")
    means=standard.get("train_feature_mean")
    stds=standard.get("train_feature_std")
    if (not isinstance(means,list) or not isinstance(stds,list)
            or len(means)!=1536 or len(stds)!=1536
            or any(type(x) not in (float,int) or not math.isfinite(x)
                   for x in means)
            or any(type(x) not in (float,int) or
                   not math.isfinite(x) or not .00001<x<100 for x in stds)):
        raise ValueError("Original source image normalization is corrupt")
    return lineage,standard,weight_file


def rebase_dense(old_weight,old_bias,old_mean,old_std,new_mean,new_std):
    """Preserve old dense features exactly under new pixel normalizers.

    For old x=(raw-old_mean)/old_std, new x=(raw-new_mean)/new_std:
    W_new = W_old * new_std / old_std;
    b_new = b_old + W_old @ ((new_mean - old_mean) / old_std).
    """
    import torch
    if (old_weight.ndim!=2 or old_bias.ndim!=1
        or old_weight.shape[0]!=old_bias.shape[0]
        or old_weight.shape[1]!=len(old_mean)
        or len(old_mean)!=len(old_std)
        or len(new_mean)!=len(old_mean)
        or len(new_std)!=len(old_mean)):
        raise ValueError("Incompatible original Mini AI image feature dimensions")
    values=[torch.as_tensor(v,device=old_weight.device,
                            dtype=old_weight.dtype) for v in
            (old_mean,old_std,new_mean,new_std)]
    prior_mu,prior_sd,current_mu,current_sd=values
    if (not all(torch.isfinite(v).all() for v in values)
        or (prior_sd<=0).any() or (current_sd<=0).any()
        or not torch.isfinite(old_weight).all()
        or not torch.isfinite(old_bias).all()):
        raise ValueError("Invalid normalized original Mini AI image parameters")
    original_w=old_weight.detach().clone()
    new_w=original_w*(current_sd/prior_sd)[None,:]
    new_bias=old_bias+original_w@((current_mu-prior_mu)/prior_sd)
    if not torch.isfinite(new_w).all() or not torch.isfinite(new_bias).all():
        raise ValueError("Source-rebased original neural weights are unstable")
    return new_w,new_bias


def warm_start(model,new_mean,new_std,folder:Path=DEFAULT):
    """Load original saved student, retain output learning, rebase pixels.

    This is merely parameter initialization. Only explicit retraining with
    previous-source rehearsal, NEW independent validation and an accepted
    forward GLB audit can claim further learned improvement.
    """
    from safetensors.torch import load_file
    lineage,normalization,weight_file=load_provenance(folder)
    state=load_file(str(weight_file),device="cpu")
    original=model.state_dict()
    if set(state)!=set(original) or any(
        state[k].shape!=original[k].shape for k in original):
        raise ValueError("Future original model architecture changed")
    adjusted_w,adjusted_b=rebase_dense(
        state["core.0.weight"],state["core.0.bias"],
        normalization["train_feature_mean"],normalization["train_feature_std"],
        new_mean,new_std)
    state["core.0.weight"]=adjusted_w
    state["core.0.bias"]=adjusted_b
    model.load_state_dict(state,strict=True)
    return {
        "schema":"assetwright-owned-native-student-warm-start-v1",
        "previous_source_sha256":lineage["saved_weights_sha256"],
        "source_training_run":lineage["research_run_id"],
        "pretrained_teacher_used":False,
        "previous_original_weight_count":lineage["parameter_count"],
        "pixel_normalizer_rebased_without_forgotten_features":True,
        "retraining_started":False,
        "requires_source_replay_and_new_blind_family":True,
        "android_deployed":False,
    }

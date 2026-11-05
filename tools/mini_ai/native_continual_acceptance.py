"""Evidence-gated cumulative Mini AI memory update.

A successful GitHub workflow is not an automatic learned improvement.
Compare the exact same fresh original Kotlin GLBs for the OLD saved neural
checkpoint and the newly fine-tuned one. A failure preserves both weights
as research, while the last verified champion stays unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from native_continual_student import SCHEMA,MODEL_SCHEMA,SEEDS,MODES
from native_continual_forward_audit import RESULT


def assess(report,geometry,model):
    if (report.get("schema")!=SCHEMA or
        geometry.get("schema")!=RESULT or
        model.get("schema")!=MODEL_SCHEMA or
        report.get("study")!="strength_continual_v4" or
        geometry.get("study_id")!="strength_continual_v4"):
        raise ValueError("Unknown native continuing learner evidence")
    if (
        report.get("prior_training_sources_rehearsed")!=672 or
        report.get("new_training_examples")!=504 or
        report.get("new_development_examples")!=96 or
        report.get("new_unseen_validation_examples")!=96 or
        report.get("prior_development_retention_examples")!=96 or
        report.get("historical_validation_leaked_into_training") is not False or
        report.get("training_sessions_completed")!=8 or
        geometry.get("fresh_original_geometry_count")!=96 or
        geometry.get("reconstructed_original_geometry_count")!=192 or
        geometry.get("independent_family_count")!=4):
        raise ValueError("Continuing training source/replay/holdout incomplete")
    if (report.get("old_prior_saved_hash")!=model.get("parent_source_checkpoint_sha256")
        or model.get("previous_stored_model_reloaded") is not True
        or model.get("old_training_replay_samples")!=672
        or model.get("fresh_new_training_samples")!=504
        or model.get("selected_on_fresh_development_only") is not True
        or report.get("warm_start_verified_from_original") is not True
        or report.get("rebased_max_logit_difference",1)>.002):
        raise ValueError("No mathematically verified actual original weight reuse")
    if (model.get("teacher_required_at_inference") is not False
        or model.get("android_deployable") is not False
        or model.get("human_review_required") is not True
        or report.get("teacher_used_in_this_training") is not False
        or report.get("external_AI_created_meshes") is not False
        or geometry.get("all_GLBS_structurally_valid") is not True
        or geometry.get("no_outside_3d") is not True
        or report.get("automatic_production_promotion") is not False):
        raise ValueError("Unsafe teacher or mobile geometry update")
    real_seconds=float(report.get("measured_training_seconds",-1))
    configured=float(report.get("configured_training_seconds",-2))
    if (not 900<=real_seconds<=2400 or
        not 900<=configured<=2100 or
        real_seconds+0.5<configured):
        raise ValueError("Continuing run failed actual gradient training budget")
    sessions=report.get("sessions",[])
    if (not isinstance(sessions,list) or len(sessions)!=8
        or {(x.get("seed"),x.get("mode")) for x in sessions}!=
            {(seed,mode) for seed in SEEDS for mode in MODES}
        or any(x.get("optimizer_updates",0)<75
               or x.get("active_training_seconds",0)<configured/8-.5
               or x.get("selected_on_new_development_only") is not True
               for x in sessions)):
        raise ValueError("Independent true warm-start training sessions incomplete")
    data=geometry.get("cases")
    if not isinstance(data,list) or len(data)!=96:
        raise ValueError("Original native GLB cases missing")
    hashes=[x.get("source_sha256") for x in data]
    if (len(set(hashes))!=96 or any(not isinstance(x,str) or len(x)!=64
        or any(y not in "0123456789abcdef" for y in x)
        for x in hashes)):
        raise ValueError("Missing or duplicate source-mesh identity")
    digest=hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()
    if not (
        digest==geometry.get("blinded_source_hashes_digest")
        ==report.get("new_blind_original_mesh_hash")
        ==model.get("fresh_validation_hash")):
        raise ValueError("New independent source SHA mismatch")
    metrics=report.get("new_blind",{})
    for key in ("prior","continued"):
        visual=metrics.get(key,{})
        real=geometry.get(key,{})
        for x,y in (("accuracy","operation_accuracy"),
                    ("strength_mae","strength_mae")):
            a=float(visual.get(x,-1))
            b=float(real.get(y,-2))
            if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>.0002:
                raise ValueError("Visual predictions differ from real generated geometry")
    prev=metrics["prior"];continued=metrics["continued"]
    old=report["old_train_prior"];retained=report["old_train_candidate"]
    gain=geometry.get("continued_geometry_gain_vs_frozen_parent_fraction",-1)
    before=geometry["prior"]["normalized_vertex_rmse"]
    after=geometry["continued"]["normalized_vertex_rmse"]
    if (not math.isfinite(gain) or before<=0 or after<0 or
        abs(gain-(before-after)/before)>.0001):
        raise ValueError("Native source reconstruction improvement inconsistent")
    unchanged=geometry.get("unchanged_source_normalized_vertex_rmse",0)
    checks={
        "old_training_operation_skill_retained":
            retained["accuracy"]>=old["accuracy"]-.02,
        "old_training_strength_skill_retained":
            retained["strength_mae"]<=old["strength_mae"]+.015,
        "fresh_operation_accuracy_not_worse_than_parent":
            continued["accuracy"]>=prev["accuracy"]-.011,
        "fresh_strength_calibration_not_regressed":
            continued["strength_mae"]<=prev["strength_mae"]+.01,
        "real_native_GLBS_at_least_2pct_better_than_parent":gain>=.02,
        "real_native_GLBS_at_least_10pct_better_than_no_change":
            unchanged>0 and after<=unchanged*.90,
        "independent_old_weights_reloaded_and_rehearsed":True,
        "separate_new_blind_sources_and_heldout_GLBS":True,
        "no_Android_automatic_promotion":True
    }
    return {
        "schema":"assetwright-forge-mini-continued-research-acceptance-v4",
        "status":"eligible_for_human_research_review"
            if all(checks.values()) else "candidate_not_promoted_parent_retained",
        "checks":checks,
        "prior_checkpoint_sha256":report["old_prior_saved_hash"],
        "new_candidate_source_hash":digest,
        "training_sessions":len(sessions),
        "active_gradient_seconds":real_seconds,
        "previous_operation_accuracy_on_fresh_blind":prev["accuracy"],
        "continued_operation_accuracy_on_fresh_blind":continued["accuracy"],
        "previous_strength_mae_on_fresh_blind":prev["strength_mae"],
        "continued_strength_mae_on_fresh_blind":continued["strength_mae"],
        "previous_vertex_rmse_on_real_GLBS":before,
        "continued_vertex_rmse_on_real_GLBS":after,
        "real_geometry_improvement_fraction":gain,
        "old_training_retention_accuracy_before":old["accuracy"],
        "old_training_retention_accuracy_after":retained["accuracy"],
        "android_installed":False,"human_visual_review_required":True,
        "parent_original_checkpoint_unchanged":True
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("evaluation","geometry","lineage","out"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    evaluation=json.loads(a.evaluation.read_text())
    geometry=json.loads(a.geometry.read_text())
    lineage=json.loads(a.lineage.read_text())
    final=assess(evaluation,geometry,lineage)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(final,indent=2)+"\n")
    print(json.dumps(final,indent=2))


if __name__=="__main__":
    main()

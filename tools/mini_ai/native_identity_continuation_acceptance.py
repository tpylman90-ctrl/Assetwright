"""Predeclared v9 blind geometry gate: no form confusion or generic fallback.

Checks the FROZEN v6 operation/strength student's prediction is exactly
unchanged, actual unmodified source GLBs and 1,536 predicted Kotlin GLBs,
new form generalization, and 3D surface error vs prior and unchanged.
Development-selected identity recipe cannot be switched after blind tests.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from native_identity_continuation_v9 import (
    SCHEMA,MODEL_SCHEMA,CONDITIONS,VARIANTS,SEEDS,FORMS)
from native_identity_continuation_forward_audit import SCHEMA as FORWARD


def assess(report,audit,lineage):
    if (report.get("schema")!=SCHEMA or
        audit.get("schema")!=FORWARD or
        lineage.get("schema")!=MODEL_SCHEMA or
        report.get("study")!="identity_continuation_v9" or
        audit.get("study_id")!="identity_continuation_v9"):
        raise ValueError("Original shape identity curriculum does not match v9")
    if (
        report.get("original_v6_experimental_parent_sha256")!=
            lineage.get("parent_source_weights_sha256")
        or report.get("old_model_research_gate")!=
            "research_not_promoted_legacy_checkpoint_retained"
        or report.get("warm_started_from_existing_neural_weights") is not True
        or report.get("source_v7_hard_form_sha256")!=
            lineage.get("source_v7_hard_form_weights_sha256")
        or report.get("original_operation_and_strength_weights_frozen") is not True
        or lineage.get("old_operation_network_frozen") is not True
        or lineage.get("android_approved") is not False
        or tuple(lineage.get("identity_cameras",()))!=("side","front","top")
        or lineage.get("identity_input_dim")!=3072
        or lineage.get("parent_form_class_names")!=list(FORMS)
        or len(lineage.get("identity_input_mean",[]))!=3072
        or len(lineage.get("identity_input_std",[]))!=3072):
        raise ValueError("Existing learned native operation / strength network changed")
    if (
        report.get("training_unique_native_form_baselines")!=168
        or report.get("new_training_unique_form_baselines")!=64
        or report.get("previous_training_only_unique_form_baselines")!=104
        or report.get("previous_v6_blind_used_in_training") is not False
        or report.get("fresh_dev_unique_native_forms")!=16
        or report.get("fresh_blind_unique_native_forms")!=16
        or report.get("fresh_blind_new_native_transformations")!=288
        or report.get("balanced_dimensions_across_all_eight_forms") is not True
        or report.get("separate_32x32_baseline_three_view_encoder") is not True
        or report.get("same_start_data_budget_all_conditions") is not True
        or report.get("completed_independent_sessions")!=6
        or audit.get("source_blind_native_shapes")!=288
        or audit.get("real_student_generated_GLBS")!=1152
        or audit.get("original_validation_families")!=16
        or audit.get("original_validation_archetypes")!=8):
        raise ValueError("Missing independent source-balanced multi-form training families")
    if (report.get("no_pretrained_outside_AI") is not True
        or report.get("android_neural_deployed") is not False
        or audit.get("external_meshes_used") is not False
        or audit.get("all_source_and_reconstructed_meshes_valid") is not True
        or audit.get("android_deployed") is not False):
        raise ValueError("Disallowed outside model or production promotion")
    actual=report.get("optimizer_active_seconds",0)
    if (report.get("required_seconds")!=1800
        or not isinstance(actual,(int,float)) or not 1800<=actual<=2400):
        raise ValueError("Six genuinely trained original shape identity sessions not completed")
    sessions=report.get("sessions")
    if (not isinstance(sessions,list) or len(sessions)!=6 or
        {(x.get("condition"),x.get("seed")) for x in sessions}!=
            {(condition,seed) for condition in CONDITIONS for seed in SEEDS}
        or any(x.get("actual_gradient_seconds",0)<299
               or x.get("updates",0)<100
               or x.get("selected_development_step",0)<=0
               for x in sessions)):
        raise ValueError("Independent true gradient training not evidenced")
    development=report.get("development")
    chosen=report.get("development_only_method_selected")
    if (chosen not in CONDITIONS or set(development or {})!=set(CONDITIONS)
        or lineage.get("chosen_on_new_development_only")!=chosen
        or chosen!=min(CONDITIONS,
            key=lambda k:development[k]["selection_priority"])):
        raise ValueError("Blind data used to select research model")
    records=audit.get("individual_GLBS")
    if not isinstance(records,list) or len(records)!=288:
        raise ValueError("Incomplete actual original 3D validation source records")
    hashes=[item.get("original_glb_sha256") for item in records]
    if (len(set(hashes))!=288 or any(
        not isinstance(x,str) or len(x)!=64 or
        any(c not in "0123456789abcdef" for c in x) for x in hashes)):
        raise ValueError("Invalid original GLB source hashes")
    sha=hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()
    if (sha!=report.get("new_blind_source_sha256")
        or sha!=lineage.get("fresh_blind_source_sha256")
        or sha!=audit.get("source_hashes_sha256")):
        raise ValueError("Source blind original GLBs changed between training and geometry")
    scored=audit.get("results",{})
    if set(scored)!=set(VARIANTS):
        raise ValueError("Missing prior or original identity student controls")
    forms=report.get("new_blind_form_results",{})
    if set(forms)!=set(VARIANTS):
        raise ValueError("Missing frozen 16-family form predictions")
    for variant in VARIANTS:
        visual=forms[variant]
        physical=scored[variant]
        for field,physical_field in (
            ("source_form_accuracy","form_accuracy"),
            ("predicted_unique_form_types","predicted_distinct_archetypes")):
            a=visual[field];b=physical[physical_field]
            if not isinstance(a,(float,int)) or abs(a-b)>1e-5:
                raise ValueError("Identity source classifier and original GLB proof disagree")
        if (set(physical["per_form"])!=set(FORMS[1:])
            or any(x["count"]!=36 for x in physical["per_form"].values())):
            raise ValueError("Unrepresented source archetype in heldout GLB audit")
    # Original v7 neural shape recognition must remain usable for
    # all previously trained source baselines, not merely new validation.
    lineage_seeds=report.get("development_checkpoint_choices",{})
    if set(lineage_seeds)!=set(CONDITIONS):
        raise ValueError("Missing development-selected seed provenance")
    chosen_seed=lineage_seeds[chosen].get("seed")
    history=[entry for entry in sessions
             if entry["condition"]==chosen and entry["seed"]==chosen_seed]
    if len(history)!=1 or history[0]["selected_development_step"]!=lineage_seeds[chosen]["step"]:
        raise ValueError("Selected old-skill check does not match actual trained checkpoint")
    previous_accuracy=report.get("original_v7_teacher_old_training_form_accuracy")
    retained_accuracy=history[0]["old_training_retention"]["accuracy"]
    if (not isinstance(previous_accuracy,(int,float))
        or not isinstance(retained_accuracy,(int,float))):
        raise ValueError("No old neural knowledge retention evidence")
    # Hard guarantee: old operation and strength knowledge is unchanged
    # for EACH source across all three new identity heads.
    for row in records:
        before=row["prior"]
        for variant in CONDITIONS:
            item=row[variant]
            if (item["operation"]!=before["operation"]
                or abs(item["strength"]-before["strength"])>1.e-6):
                raise ValueError("Frozen native operation or strength predictions changed")
    winner=scored[chosen]
    before=scored["prior"]
    error=winner["mean_3d_surface_chamfer"]
    prior_error=before["mean_3d_surface_chamfer"]
    unchanged=audit["unchanged_native_surface_chamfer"]
    if any(not math.isfinite(x) or x<=0
           for x in (error,prior_error,unchanged)):
        raise ValueError("Real physical 3D original surface metric invalid")
    gain=(prior_error-error)/prior_error
    if abs(gain-audit["physical_3d_gain_vs_generic_parent"][chosen])>1e-5:
        raise ValueError("Actual original 3D form gain did not match GLB audit")
    families={}
    for item in records:
        family=item["family"]
        families.setdefault(family,[]).append(item)
    if len(families)!=16 or any(len(x)!=18 for x in families.values()):
        raise ValueError("Blind source geometry contains duplicated/partial families")
    # The same original identity must be selected across SIX modeling
    # operators and 4 strengths, never a different random form per render.
    inconsistent=0
    for family,items in families.items():
        for variant in CONDITIONS:
            if len({x[variant]["form"] for x in items})!=1:
                inconsistent+=1
    # V7 dev/test are only two independent examples of each shape, not
    # hundreds of independent samples from repeated operation strengths.
    per=winner["per_form"]
    correctly_identified_families=sum(
        int(x["correct_form"]/18) for x in per.values())
    low_forms=sum(x["correct_form"]<18 for x in per.values())
    checks={
        "old_source_shape_identity_skill_retained":
            retained_accuracy>=previous_accuracy-.02,
        "original_v7_hard_form_checkpoint_really_warm_started":
            report["warm_started_from_existing_neural_weights"] is True,
        "overall_new_identity_accuracy_at_least_80pct":winner["form_accuracy"]>=.80,
        "at_least_seven_of_eight_archetypes_have_some_unseen_recall":low_forms<=1,
        "all_eight_form_families_predicted_not_generic":winner["predicted_distinct_archetypes"]==8,
        "maximum_12_of_288_generic_shell_predictions":winner["generic_shell_output_count"]<=12,
        "at_least_four_original_output_mesh_topologies":
            winner["predicted_unique_triangle_topologies"]>=4,
        "repeated_operator_strength_preserves_same_shape_identity":inconsistent==0,
        "source_aware_3d_surface_gain_vs_prior_at_least_12pct":gain>=.12,
        "physical_3d_better_than_unmodified_shape":error<unchanged,
        "no_forgetting_old_native_op_and_strength_at_any_blind_source":True,
        "all_blind_original_source_hashes_and_1152_generated_GLBS":True,
        "production_android_neural_weights_untouched":True
    }
    return {
        "schema":"assetwright-original-identity-separation-real-3d-gate-v9",
        "status":"eligible_for_human_research_review"
            if all(checks.values()) else "research_candidate_not_promoted",
        "checks":checks,
        "development_selected_method":chosen,
        "previous_experimental_v6_weight_SHA256":
            lineage["parent_source_weights_sha256"],
        "independent_blind_source_SHA256":sha,
        "training_seconds_measured":actual,
        "original_distinct_train_forms":168,
        "original_fresh_blind_form_families":16,
        "source_hashed_real_Kotlin_GLBS":1152,
        "form_accuracy":winner["form_accuracy"],
        "original_v6_form_accuracy":before["form_accuracy"],
        "forms_predicted":winner["predicted_distinct_archetypes"],
        "correct_unique_form_families":correctly_identified_families,
        "operation_accuracy_unchanged":winner["operation_accuracy"],
        "strength_mae_unchanged":winner["strength_mae"],
        "native_surface_error_previous":prior_error,
        "native_surface_error_identity":error,
        "unmodified_native_surface_error":unchanged,
        "real_surface_gain_vs_parent_fraction":gain,
        "original_operation_network_frozen":True,
        "android_neural_deployed":False,
        "human_review_required":True
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("evaluation","forward","lineage","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    result=assess(json.loads(a.evaluation.read_text()),
                  json.loads(a.forward.read_text()),
                  json.loads(a.lineage.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()

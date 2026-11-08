"""Independent original form/geometry v8 no-leakage and no-regression gate."""
from __future__ import annotations
import hashlib
import os
import unittest

from advanced_form_student import OPERATIONS
from dino_delta_school import STUDY,FAMILIES,LEVELS,EXPECTED,BASELINES,expected_changes
from native_geometry_mastery_v10 import SCHEMA,WEIGHT_SCHEMA,CONDITIONS,VARIANTS
from native_geometry_mastery_forward_audit import SCHEMA as FORWARD
from native_geometry_mastery_acceptance import assess


def fake(geometry_is_better=True):
    records=[]
    for family in FAMILIES["validation"]:
        form=("SPINDLE","WEDGE","BOX_MODULE","BARREL",
              "ARCH","BLADE","CANOPY_POD","TRUSS_BEAM")[
                  (int(family[-2:])-1)%8]
        for op in OPERATIONS:
            for p in LEVELS["validation"]:
                case=(f"validation__{family}__{op.lower()}__"
                      f"s{round(p*1000):03d}")
                row={
                    "case":case,"family":family,
                    "target_form":form,"target_operation":op,
                    "target_strength":p,
                    "original_glb_sha256":hashlib.sha256(case.encode()).hexdigest()
                }
                for name in VARIANTS:
                    row[name]={"form":form,"strength":p,
                               "operation":op}
                records.append(row)
    assert len(records)==288
    sha=hashlib.sha256("\n".join(sorted(
        r["original_glb_sha256"] for r in records)).encode()).hexdigest()
    rmse={
        "parent_v8_with_v9_forms":.025,
        "warm_replay":.021,
        "vertex_geometry":.018 if geometry_is_better else .027,
        "geometry_rank":.019
    }
    physical={
        name:{
            "form_accuracy":.875,
            "operation_accuracy":.83 if name=="parent_v8_with_v9_forms" else .90,
            "strength_mae":.21 if name=="parent_v8_with_v9_forms" else .16,
            "mean_3d_surface_chamfer":rmse[name],
            "predicted_distinct_archetypes":8,
            "predicted_unique_triangle_topologies":6,
            "generic_shell_output_count":0,
            "per_form":{
                form:{"count":36}
                for form in ("SPINDLE","WEDGE","BOX_MODULE","BARREL",
                             "ARCH","BLADE","CANOPY_POD","TRUSS_BEAM")
            }
        } for name in VARIANTS
    }
    audit={
        "schema":FORWARD,"study_id":"geometry_mastery_v10",
        "source_blind_native_shapes":288,
        "real_student_generated_GLBS":1152,
        "original_validation_families":16,
        "original_validation_archetypes":8,
        "source_hashes_sha256":sha,
        "external_meshes_used":False,
        "android_deployed":False,
        "all_source_and_reconstructed_meshes_valid":True,
        "reconstruction_form_chosen_by":
            "actual student neural form head, never target form",
        "results":physical,
        "individual_GLBS":records,
        "unchanged_native_surface_chamfer":.022,
        "physical_3d_gain_vs_generic_parent":{
            name:(rmse["parent_v8_with_v9_forms"]-rmse[name])/rmse["parent_v8_with_v9_forms"]
            for name in CONDITIONS
        }
    }
    stats={
        "operation_accuracy":.94,
        "strength_mae":.08,
        "native_3D_displacement_proxy_rmse":.008,
    }
    sessions=[{
        "condition":name,"seed":seed,
        "actual_optimizer_seconds":300.01,
        "optimizer_updates":1152,"selected_development_step":600,
        "old_training_retention":stats
    } for name in CONDITIONS for seed in (413,2027)]
    report={
        "schema":SCHEMA,"study":"geometry_mastery_v10",
        "both_existing_neural_networks_frozen":True,
        "old_v6_experimental_parent_sha256":"a"*64,
        "old_v7_experimental_identity_sha256":"b"*64,
        "old_v8_trained_adapter_sha256":"c"*64,
        "old_v9_form_checkpoint_sha256":"d"*64,
        "actual_original_v8_adapter_warm_started":True,
        "actual_original_v9_form_head_loaded":True,
        "older_correct_original_train_sources":1152,
        "new_original_shape_train_examples":1152,
        "new_development_examples":288,
        "new_fresh_unseen_blind_examples":288,
        "new_shape_train_families":48,
        "fresh_blind_form_families":16,
        "three_methods_equal_start_and_cpu_time":True,
        "geometry_supervision_only_original_kotlin_GLBS":True,
        "external_teacher_used":False,
        "android_neural_deployed":False,
        "configured_optimizer_seconds":1800,
        "measured_optimizer_seconds":1800.06,
        "completed_sessions":6,"sessions":sessions,
        "development_selected":"vertex_geometry",
        "development_checkpoint_seeds":{
            name:{"seed":413,"selected_step":600}
            for name in CONDITIONS
        },
        "development_results":{
            "warm_replay":{"development_priority":.84},
            "vertex_geometry":{"development_priority":.61},
            "geometry_rank":{"development_priority":.72},
        },
        "previous_training_retention_before":stats,
        "blind_source_sha256":sha,
        "blind_per_method_predictions":{
            name:{
                "form_accuracy":j["form_accuracy"],
                "operation_accuracy":j["operation_accuracy"],
                "strength_mae":j["strength_mae"],
                "predicted_distinct_forms":j["predicted_distinct_archetypes"]
            } for name,j in physical.items()
        }
    }
    lineage={
        "schema":WEIGHT_SCHEMA,
        "source_v6_weight_sha256":"a"*64,
        "source_v7_form_weight_sha256":"b"*64,
        "legacy_action_weights_frozen":True,
        "legacy_shape_identity_weights_frozen":True,
        "source_v8_adapter_sha256":"c"*64,
        "source_v9_identity_sha256":"d"*64,
        "v8_adapter_weights_warm_started":True,
        "v9_form_head_weights_frozen":True,
        "final_method_selected_by_new_development":"vertex_geometry",
        "blind_source_sha256":sha,
        "not_approved_for_android":True,
        "ops":list(OPERATIONS)
    }
    return report,audit,lineage


@unittest.skipUnless(os.getenv("ASSETWRIGHT_DINO_STUDY")=="geometry_mastery_v10",
                     "Source-disjoint geometry v8 test requires matching study")
class NativeFormFidelityGate(unittest.TestCase):
    def test_new_eight_archetype_source_curriculum_and_holdout(self):
        self.assertEqual(STUDY,"geometry_mastery_v10")
        self.assertEqual(EXPECTED,1728)
        self.assertEqual(BASELINES,80)
        self.assertEqual(len(expected_changes()),1728)
        self.assertEqual({s:len(FAMILIES[s]) for s in FAMILIES},{
            "train":48,"development":16,"validation":16})
        self.assertEqual({s:sum(x[0]==s for x in expected_changes().values())
                          for s in FAMILIES},{
            "train":1152,"development":288,"validation":288})
        self.assertTrue(all(s.startswith("gm_blind")
                            for s in FAMILIES["validation"]))
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))

    def test_physical_3D_improvement_only_qualifies_for_human_review(self):
        result=assess(*fake())
        self.assertEqual(result["status"],"eligible_for_human_research_review")
        self.assertTrue(result["older_neural_weights_untouched"])
        self.assertFalse(result["android_deployed"])

    def test_bad_real_3d_fidelity_keeps_previous_parent(self):
        result=assess(*fake(False))
        self.assertEqual(result["status"],
            "experimental_checkpoint_not_promoted_parent_protected")
        self.assertFalse(result["checks"][
            "real_3D_surface_improved_vs_old_student_at_least_8pct"])

    def test_no_blind_posthoc_model_choice(self):
        a,b,c=fake()
        a["development_selected"]="geometry_rank"
        with self.assertRaisesRegex(ValueError,"post-hoc"):
            assess(a,b,c)

    def test_original_form_or_source_hash_cannot_change(self):
        a,b,c=fake()
        b["individual_GLBS"][0]["vertex_geometry"]["form"]="WEDGE"
        # A form substitution must be checked across variants before gating.
        result=assess(a,b,c)
        self.assertFalse(result["checks"][
            "all_variants_use_same_frozen_original_form_identity"])
        a,b,c=fake()
        b["source_hashes_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"checksums"):
            assess(a,b,c)

    def test_research_failures_dont_hide_missing_training_or_external_AI(self):
        a,b,c=fake()
        a["measured_optimizer_seconds"]=20
        with self.assertRaisesRegex(ValueError,"CPU gradient"):
            assess(a,b,c)
        a,b,c=fake()
        a["external_teacher_used"]=True
        with self.assertRaisesRegex(ValueError,"Outside mesh"):
            assess(a,b,c)


if __name__=="__main__":
    unittest.main()

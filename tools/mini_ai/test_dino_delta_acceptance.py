"""Release guard: no teacher-only image success can approve mobile 3D."""
import unittest
from dino_delta_acceptance import gate


def fixture(accepted):
    acc=.8 if accepted else .25
    mae=.08 if accepted else .225
    pair_joint=.12 if accepted else -.01
    dino_joint=.07 if accepted else .015
    geom=.21 if accepted else .015
    vs_pair=.06 if accepted else -.03
    metrics={
        "paired_without_DINO":{"accuracy":acc-.03,"strength_mae":mae+.005},
        "paired_with_DINO":{"accuracy":acc,"strength_mae":mae}
    }
    visual={
        "schema":"assetwright-native-before-after-visual-comparison-v1",
        "fresh_validation_examples":54,
        "original_kotlin_glbs":486,"native_before_after_pairs":468,
        "heldout_modified_source_hashes_sha256":"a"*64,
        "model_inference_requires_DINO":False,
        "external_AI_generates_3d":False,
        "metrics":metrics,
        "before_after_joint_improvement_fraction":pair_joint,
        "DINO_joint_improvement_vs_paired":dino_joint,
        "status":"provisional_visual_transfer_pass" if accepted else "visual_transfer_not_yet_validated"
    }
    forward={
        "schema":"assetwright-native-before-after-forward-audit-v1",
        "fresh_original_target_glbs":54,
        "real_student_generated_glbs":108,
        "source_hashes_sha256":"a"*64,
        "all_native_glbs_structurally_audited":True,
        "external_AI_used_to_generate_meshes":False,
        "paired_teacher_free":{"operation_accuracy":acc-.03,"strength_mae":mae+.005},
        "paired_with_DINO":{"operation_accuracy":acc,"strength_mae":mae},
        "improvement_over_unchanged_native_fraction":geom,
        "DINO_improvement_over_paired_without_teacher_fraction":vs_pair,
        "status":"forward_reconstruction_pass" if accepted else "forward_reconstruction_not_validated"
    }
    model={
        "schema":"assetwright-original-before-after-native-student-v1",
        "generator_authority":"AssetWright-Kotlin-AdvancedFormLab",
        "teacher_required_at_inference":False,
        "android_deployable":False,
        "approved_for_geometry_generation":False
    }
    return visual,forward,model


class PairedNativeAcceptanceTests(unittest.TestCase):
    def test_underperforming_dino_not_approved_even_if_valid_meshes(self):
        result=gate(*fixture(False))
        self.assertEqual(result["status"],"research_candidate_not_approved")
        self.assertFalse(result["checks"]["native_operator_accuracy"])
        self.assertFalse(result["automatic_promotion"])

    def test_even_passing_research_requires_human_review(self):
        result=gate(*fixture(True))
        self.assertEqual(result["status"],"eligible_for_human_research_review")
        self.assertFalse(result["android_deployable"])
        self.assertTrue(result["human_visual_review_required"])

    def test_cross_verified_model_predictions_and_source_hashes_required(self):
        a,b,c=fixture(True)
        b["source_hashes_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"different source hashes"):
            gate(a,b,c)
        a,b,c=fixture(True)
        b["paired_with_DINO"]["operation_accuracy"]-=.1
        with self.assertRaisesRegex(ValueError,"disagree"):
            gate(a,b,c)
        a,b,c=fixture(True)
        c["teacher_required_at_inference"]=True
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            gate(a,b,c)

    def test_do_not_trust_report_status_without_real_thresholds(self):
        a,b,c=fixture(True)
        a["metrics"]["paired_with_DINO"]["accuracy"]=.25
        b["paired_with_DINO"]["operation_accuracy"]=.25
        self.assertEqual(gate(a,b,c)["status"],"research_candidate_not_approved")
        a,b,c=fixture(True)
        b["improvement_over_unchanged_native_fraction"]=.02
        self.assertEqual(gate(a,b,c)["status"],"research_candidate_not_approved")


if __name__=="__main__":
    unittest.main()

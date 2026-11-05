"""Fail-closed end-to-end DINO image student + actual native GLB promotion."""
import hashlib
import unittest

from dino_native_acceptance_gate import disposition


def evidence(accepted=False):
    hashes=[hashlib.sha256(str(i).encode()).hexdigest() for i in range(36)]
    canonical=hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()
    accuracy=.75 if accepted else .25
    strength=.08 if accepted else .22
    baseline=.05
    student_err=.04 if accepted else .049
    gain=(baseline-student_err)/baseline
    visual={
        "schema":"assetwright-original-geometry-dino-visual-study-v1",
        "official_unseen_native_glbs":36,
        "heldout_source_sha256":canonical,
        "teacher_generates_3d":False,
        "pixel_student_requires_teacher_at_inference":False,
        "status":"validated_research_visual_to_native" if accepted else "rejected_visual_teacher_transfer",
        "teacher_distilled_student":{"accuracy":accuracy,"strength_mae":strength},
        "evaluation_improvement":{"joint_fraction":.05 if accepted else .01}
    }
    forward={
        "schema":"assetwright-dino-original-forward-native-glb-audit-v1",
        "actual_original_target_glbs":36,
        "actual_student_reconstructed_glbs":36,
        "actual_constant_baseline_glbs":36,
        "all_meshes_independently_structurally_valid":True,
        "external_ai_meshes_used":False,
        "predicted_operator_accuracy":accuracy,
        "predicted_strength_mae":strength,
        "student_mean_normalized_vertex_rmse":student_err,
        "constant_mean_normalized_vertex_rmse":baseline,
        "forward_improvement_fraction":gain,
        "strict_forward_geometry_gate":accepted,
        "cases":[{"target_source_sha256":s} for s in hashes],
    }
    student={
        "schema":"assetwright-owned-image-native-operator-student-v1",
        "teacher_runtime_required":False,"android_deployable":False,
        "approved_for_geometry_generation":False
    }
    return visual,forward,student


class NativeVisualPromotionTests(unittest.TestCase):
    def test_honestly_rejects_underperforming_student(self):
        doc=disposition(*evidence())
        self.assertEqual(doc["status"],"research_candidate_rejected")
        self.assertFalse(doc["checks"]["independent_forward_geometry_gate"])
        self.assertFalse(doc["automatic_geometry_generation_approval"])

    def test_even_validated_research_never_auto_deploys(self):
        doc=disposition(*evidence(True))
        self.assertEqual(doc["status"],"eligible_for_human_research_review")
        self.assertFalse(doc["android_deployable"])
        self.assertTrue(doc["human_approval_required"])

    def test_visual_source_hashes_must_match_real_reconstructed_glbs(self):
        a,b,c=evidence(True)
        b["cases"][0]["target_source_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"different GLBs"):
            disposition(a,b,c)

    def test_rejects_inconsistent_predictions_and_unverified_teacher(self):
        a,b,c=evidence(True)
        b["predicted_operator_accuracy"]=.5
        with self.assertRaisesRegex(ValueError,"disagree"):
            disposition(a,b,c)
        a,b,c=evidence(True)
        c["teacher_runtime_required"]=True
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            disposition(a,b,c)

    def test_does_not_trust_boolean_pass_flags_without_independent_metrics(self):
        a,b,c=evidence(True)
        a["teacher_distilled_student"]["accuracy"]=.25
        b["predicted_operator_accuracy"]=.25
        result=disposition(a,b,c)
        self.assertEqual(result["status"],"research_candidate_rejected")
        a,b,c=evidence(True)
        b["forward_improvement_fraction"]=.7
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            disposition(a,b,c)


if __name__=="__main__":
    unittest.main()

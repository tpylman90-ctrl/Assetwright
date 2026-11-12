"""Test that v12 model selection is native development geometry, never blind."""
import os
import unittest
from native_resolution_aware_v12 import SCHEMA,WEIGHT_SCHEMA,VARIANTS
from native_resolution_aware_forward_audit import SCHEMA as FORWARD
from select_native_resolution_aware_v12 import select


def fake():
    report={
        "schema":SCHEMA,
        "configured_optimizer_seconds":900,
        "completed_sessions":3,
        "source_baseline_topology_available_at_inference":True,
    }
    lineage={"schema":WEIGHT_SCHEMA}
    measures={}
    for name,loss in (
        ("parent_v10",.04),("replay_control_stage1",.037),
        ("vertex_loss_stage1",.031),("ranking_loss_stage1",.032)):
        measures[name]={
            "form_accuracy":1.0,"operation_accuracy":.95,
            "strength_mae":.10,"mean_3d_surface_chamfer":loss,
            "predicted_distinct_archetypes":8,
            "predicted_unique_triangle_topologies":4,
            "generic_shell_output_count":0
        }
    dev={
        "schema":FORWARD,"study_id":"resolution_aware_v12",
        "evaluated_split":"development",
        "source_blind_native_shapes":288,
        "real_student_generated_GLBS":1152,
        "input_resolution_verified_from_unmodified_GLBS":True,
        "all_source_and_reconstructed_meshes_valid":True,
        "source_hashes_sha256":"f"*64,
        "results":measures
    }
    return report,dev,lineage


class TopologyMatchedSelection(unittest.TestCase):
    def test_prefers_lower_real_original_dev_chamfer(self):
        winner=select(*fake())
        self.assertEqual(winner["selected"],"vertex_loss_stage1")
        self.assertAlmostEqual(winner["physical_development_gain_vs_parent_fraction"],.225)
        self.assertTrue(winner["selected_without_blind_3D_audit"])
    def test_cannot_use_blind_split_to_select(self):
        r,d,l=fake()
        d["evaluated_split"]="validation"
        with self.assertRaisesRegex(ValueError,"development geometry"):
            select(r,d,l)
    def test_no_skill_regression_shortcut(self):
        r,d,l=fake()
        d["results"]["vertex_loss_stage1"]["operation_accuracy"]=.2
        self.assertEqual(select(r,d,l)["selected"],"ranking_loss_stage1")
    def test_requires_1152_true_native_development_meshes(self):
        r,d,l=fake()
        d["real_student_generated_GLBS"]=3
        with self.assertRaises(ValueError):
            select(r,d,l)


if __name__=="__main__":
    unittest.main()

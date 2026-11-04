"""Unit tests only; arithmetic fixtures never count as GLB evidence."""
from __future__ import annotations
import unittest
import numpy as np
from native_composition_student import (
    PAIRS,ORDER,TOTAL,expected_stems,fit_student,predict,acceptance
)

class NativeCompositionStudentTest(unittest.TestCase):
    def test_exact_batch_and_20_composition_programs(self):
        self.assertEqual(20,len(PAIRS))
        self.assertEqual(1120,len(expected_stems()))
        self.assertEqual(TOTAL,1120)
        self.assertEqual(6,len(ORDER))
        self.assertEqual(len(set(PAIRS)),20)

    def training_rows(self):
        # Synthetic numerical isolation fixture: not real mesh evidence.
        rows=[]
        for family in range(10):
            for plan,pair in enumerate(PAIRS):
                for slot in range(4):
                    y=np.zeros(6)
                    for k,idx in enumerate(pair):
                        y[idx]=.25+.07*slot+.025*k+.003*family
                    x=np.zeros(57)
                    x[:6]=y
                    x[6:12]=y*.5
                    rows.append({"phase":"train","plan":plan,"targets":y,
                        "features":x,"source_sha256":f"fixture-{family}-{plan}-{slot}"})
        return rows

    def test_real_original_regression_fits_multiop_learning_problem(self):
        rows=self.training_rows()
        model=fit_student(rows)
        self.assertFalse(model["android_deployable"])
        estimated,selected=predict(model,rows[0]["features"])
        self.assertEqual((1,6),estimated.shape)
        self.assertEqual((1,3),selected.shape)
        self.assertEqual(set(PAIRS[0]),set(selected[0]))
        self.assertLess(np.abs(estimated[0]-rows[0]["targets"]).mean(),.04)

    def test_training_partition_is_strict(self):
        rows=self.training_rows()
        with self.assertRaises(ValueError): fit_student(rows[:799])
        wrong=[dict(r) for r in rows]
        wrong[1]["phase"]="validation"
        with self.assertRaises(ValueError): fit_student(wrong)

    def test_acceptance_gates_cannot_be_trivially_weakened(self):
        metrics={"exact_three_operation_plan_accuracy":.5,
                 "active_strength_mae":.20,
                 "constant_point_five_active_baseline_mae":.22,
                 "per_operation":{op:{"recall":.5} for op in ORDER}}
        self.assertFalse(all(acceptance(metrics,metrics).values()))

if __name__=="__main__":
    unittest.main()

"""Arithmetic-only unit checks; not substitutes for original source GLB audits."""
import unittest
try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("Native interface research requires optional NumPy")
from native_interface_student import (
    expected_stems, expected_recipe, fit, infer, acceptance
)

class NativeInterfaceStudentTest(unittest.TestCase):
    def rows(self):
        rows=[]
        for f in range(1,13):
            for i in range(30):
                y=expected_recipe("train",f,i)
                x=np.array([.14+.34*y[0],.08+.35*y[1],
                    (.16+.12*y[2])*(32/35),.01+(.02*y[1])])
                rows.append({"phase":"train","strengths":y,
                             "features":x,"sha":f"synthetic-{f}-{i}"})
        return rows

    def test_batch_and_from_scratch_regression(self):
        self.assertEqual(480,len(expected_stems()))
        rows=self.rows()
        model=fit(rows)
        prediction=infer(model,np.stack([r["features"] for r in rows]))
        expected=np.stack([r["strengths"] for r in rows])
        self.assertLess(np.abs(prediction-expected).mean(),.01)
        self.assertEqual(model["source_glbs"],360)
        self.assertFalse(model["android_deployable"])

    def test_source_split_rejection(self):
        rows=self.rows()
        with self.assertRaises(ValueError):fit(rows[:-1])
        wrong=[dict(row) for row in rows]
        wrong[0]["phase"]="validation"
        with self.assertRaises(ValueError):fit(wrong)

    def test_acceptance_cannot_promote_weak_model(self):
        weak={"mean_parameter_mae":.1,
              "per_control_mae":{k:.1 for k in (
                  "bore_strength","flange_strength","blend_strength")},
              "constant_point_five_baseline_mae":.19,
              "max_parameter_error":.2}
        self.assertFalse(all(acceptance(weak,weak).values()))

if __name__=="__main__":
    unittest.main()
